# SPDX-License-Identifier: Apache-2.0
"""Synchronous, scenario-scoped JSONL evidence without ROS or live RDF graphs."""

import json
from collections.abc import Iterator, Mapping
from math import isfinite
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from rdflib import URIRef

SCHEMA_VERSION = 1


def _validate_timestamp(stamp: float | None) -> None:
    if stamp is None:
        return
    try:
        finite = not isinstance(stamp, bool) and isfinite(stamp)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError("A timestamp must be finite seconds")


class ProvenanceJournal:
    """Record scenario evidence linked to its RDF model in one clock domain.

    Callers coordinate access and handle recording errors.

    Parameters:
        path: new JSONL file; existing files are never overwritten
        context_id: scenario context UUID
        use_sim_time: True for simulation seconds, False for wall-clock Unix seconds
    """

    def __init__(
        self,
        path: str | Path,
        context_id: UUID,
        use_sim_time: bool,
    ) -> None:
        self.context_id = str(context_id)
        self.trs_id = URIRef(f"{context_id.urn}#clock") if use_sim_time else None
        self._samples: dict[int, tuple[URIRef, float]] = {}
        self._closed = False
        self._failed = False
        self._stream = Path(path).open("xb")  # noqa: SIM115 - owned until close()/__exit__
        try:
            self.create_record(
                URIRef(context_id.urn),
                None,
                data={"use_sim_time": use_sim_time, "trs_id": self.trs_id},
            )
        except BaseException:
            self._stream.close()
            raise

    @property
    def failed(self) -> bool:
        """Whether a write, flush, or close failed; this journal cannot accept more records."""
        return self._failed

    def create_record(
        self,
        model_uri: URIRef,
        stamp: float | None,
        data: Mapping[str, Any] | None = None,
    ) -> UUID:
        """Create and append a record with a fresh UUID, returning that UUID.

        Validation and I/O errors propagate; existing records are never updated.

        Parameters:
            model_uri: observation, policy, event or configuration URI in the captured RDF model
            stamp: effective seconds; None omits the timestamp from the record
            data: record-specific JSON-compatible mapping; None omits the field
        """
        if self._closed or self._failed:
            raise OSError("Provenance journal is closed or failed")
        if not model_uri:
            raise ValueError("A record must reference a model URI")
        _validate_timestamp(stamp)
        record_id = uuid4()
        record = {
            "schema_version": SCHEMA_VERSION,
            "model_uri": model_uri,
            "record_id": str(record_id),
            "scenario_context_id": self.context_id,
        }
        if data is not None:
            record["data"] = data
        if stamp is not None:
            record["stamp"] = stamp

        def map_as_dict(value):
            """Convert non-dict mappings to dict for json serialization."""
            if isinstance(value, Mapping):
                return dict(value)
            raise TypeError("Data must contain JSON-compatible values")

        line = (
            json.dumps(record, default=map_as_dict, allow_nan=False, separators=(",", ":")) + "\n"
        ).encode("utf-8")

        try:
            if self._stream.write(line) != len(line):
                raise OSError("Short provenance journal write")
            self._stream.flush()
        except (OSError, ValueError):
            self._failed = True
            raise
        return record_id

    def record_observation(
        self,
        sample_id: int,
        observation_uri: URIRef,
        stamp: float,
    ) -> UUID | None:
        """Write a sample once, returning its record UUID or None if already recorded.

        Parameters:
            sample_id: normalized sample ID, scoped by this scenario context
            observation_uri: modeled observation URIRef
            stamp: sample timestamp in the scenario clock domain

        Reusing an ID with different metadata raises ValueError. Providers resolve
        through the observation URI in the captured model.
        """
        if self._closed or self._failed:
            raise OSError("Provenance journal is closed or failed")
        if type(sample_id) is not int or sample_id < 0 or not observation_uri:
            raise ValueError("A sample needs a nonnegative integer ID and observation URI")
        _validate_timestamp(stamp)
        metadata = (observation_uri, stamp)
        previous = self._samples.get(sample_id)
        if previous is not None:
            if previous != metadata:
                raise ValueError("A sample ID cannot change observation or timestamp")
            return None
        record_id = self.create_record(observation_uri, stamp, {"sample_id": sample_id})
        self._samples[sample_id] = metadata
        return record_id

    def record_evaluation(
        self,
        policy_uri: URIRef,
        stamp: float,
        result: bool | str | None,
        details: Mapping[str, Any],
    ) -> UUID:
        """Write an evaluation referencing recorded samples and return its record UUID.

        Parameters:
            policy_uri: modeled policy URIRef, serialized directly as a JSON string
            stamp: effective trinary evaluation timestamp
            result: True, False, "unknown", or None (no result); adapt trinary objects in the callback
            details: evaluator-selected evidence, with sample_ids referencing recorded observations

        The policy URI is stored as model_uri; its type comes from the captured model.
        Details are passed directly to the writer without mutation. Invalid references,
        unsupported details and write failures raise to the recording callback.
        """
        if not policy_uri or not (result is None or type(result) is bool or result == "unknown"):
            raise ValueError("An evaluation needs a policy URI and a supported trinary result")
        _validate_timestamp(stamp)
        references = details.get("sample_ids", ())
        if not isinstance(references, (list, tuple)) or any(
            type(sample_id) is not int or sample_id not in self._samples for sample_id in references
        ):
            raise ValueError("Evaluation sample IDs must reference recorded observations")
        return self.create_record(policy_uri, stamp, {"result": result, "details": details})

    def close(self) -> None:
        """Close once. Report close failures to the caller and reject subsequent writes."""
        if not self._closed:
            self._closed = True
            try:
                self._stream.close()
            except (OSError, ValueError):
                self._failed = True
                raise

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def read_journal(path: str | Path) -> Iterator[dict[str, Any]]:
    """Read and validate ordered journal records, restoring UUID and URIRef identifiers.

    Ignore an unterminated final line; reject malformed complete records.

    Parameters:
        path: journal file to read
    """

    def reject_constant(value):
        raise ValueError(f"Nonfinite JSON constant: {value}")

    context_id = None
    record_ids = set()
    with Path(path).open("rb") as stream:
        for index, line in enumerate(stream):
            if not line.endswith(b"\n"):
                return
            record = json.loads(line, parse_constant=reject_constant)
            if (
                not isinstance(record, dict)
                or type(record.get("schema_version")) is not int
                or record["schema_version"] != SCHEMA_VERSION
                or not isinstance(record.get("record_id"), str)
                or not isinstance(record.get("model_uri"), str)
                or record.get("stamp") is not None
                and not isinstance(record["stamp"], (int, float))
                or record.get("data") is not None
                and not isinstance(record["data"], dict)
            ):
                raise ValueError(f"Invalid journal record at line {index + 1}")
            record_id = UUID(record["record_id"])
            if str(record_id) != record["record_id"] or record_id in record_ids:
                raise ValueError("Invalid or duplicate record UUID")
            record_ids.add(record_id)
            record["record_id"] = record_id
            record["model_uri"] = URIRef(record["model_uri"])
            if not record["model_uri"]:
                raise ValueError("A record must reference a model URI")
            current = record.get("scenario_context_id")
            if not isinstance(current, str) or str(UUID(current)) != current:
                raise ValueError("Invalid scenario context UUID")
            if context_id is not None and current != context_id:
                raise ValueError("A journal cannot contain multiple scenario contexts")
            context_id = current
            if index == 0:
                metadata = record.get("data")
                if (
                    record["model_uri"] != URIRef(UUID(current).urn)
                    or not isinstance(metadata, dict)
                    or type(metadata.get("use_sim_time")) is not bool
                    or "trs_id" not in metadata
                ):
                    raise ValueError(
                        "The first record must declare the scenario clock mode and TRS"
                    )
                trs_id = metadata["trs_id"]
                if metadata["use_sim_time"]:
                    if not isinstance(trs_id, str) or not trs_id:
                        raise ValueError("A simulation clock needs a nonempty TRS URI")
                    metadata["trs_id"] = URIRef(trs_id)
                elif trs_id is not None:
                    raise ValueError("Wall-clock metadata must not declare a custom TRS")
            _validate_timestamp(record.get("stamp"))
            yield record
