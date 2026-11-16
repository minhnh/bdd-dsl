# SPDX-License-Identifier: Apache-2.0
"""Scenario-scoped RDF provenance and synchronous JSONL evidence without ROS."""

import json
from collections.abc import Iterator
from math import isfinite
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from rdf_utils.models.prov import create_bundle
from rdf_utils.models.time import add_trs
from rdflib import RDF, Dataset, URIRef
from rdflib.namespace import PROV
from trinary import Unknown

SCHEMA_VERSION = 2
TRINARY_REPS = {True: True, False: False, Unknown: "unknown", None: None}


def _validate_timestamp(stamp: float) -> None:
    try:
        finite = not isinstance(stamp, bool) and isfinite(stamp)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError("A timestamp must be finite seconds")


class ProvenanceJournal:
    """Own an execution bundle and record JSONL evidence in its clock domain.

    Callers coordinate access and handle recording errors.

    Parameters:
        path: new JSONL file; existing files are never overwritten
        context_id: scenario context UUID
        use_sim_time: True for simulation seconds, False for wall-clock Unix seconds
        dataset: Shared dataset receiving the execution bundle.
        agent_id: Software agent associated with the execution and its bundle.
    """

    def __init__(
        self,
        path: str | Path,
        context_id: UUID,
        use_sim_time: bool,
        *,
        dataset: Dataset,
        agent_id: URIRef,
    ) -> None:
        self.path = Path(path)
        self._samples: dict[int, tuple[URIRef, float]] = {}
        self._closed = False
        self._failed = False
        self._stream = self.path.open("xb")

        self.dataset = dataset
        self.execution_id = URIRef(context_id.urn)
        self.bundle_id = create_bundle(dataset, agent_id)
        self.graph = dataset.graph(self.bundle_id)
        self.graph.add((self.execution_id, RDF.type, PROV.Activity))
        self.graph.add((self.execution_id, PROV.wasAssociatedWith, agent_id))
        dataset.default_graph.add((self.bundle_id, PROV.wasGeneratedBy, self.execution_id))

        self.trs_id = None
        if use_sim_time:
            self.trs_id = add_trs(self.graph)
            self.graph.add((self.execution_id, PROV.used, self.trs_id))

    @property
    def failed(self) -> bool:
        """Whether a write, flush, or close failed; this journal cannot accept more records."""
        return self._failed

    def create_record(
        self,
        model_uri: URIRef,
        stamp: float,
        data: dict[str, Any] | None = None,
    ) -> UUID:
        """Create and append a record with a fresh UUID, returning that UUID.

        Validation and I/O errors propagate; existing records are never updated.

        Parameters:
            model_uri: observation, policy, event or configuration URI in the captured RDF model
            stamp: effective seconds in the scenario clock domain
            data: record-specific JSON-compatible dictionary; None omits the field
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
            "execution_id": self.execution_id,
        }
        if data is not None:
            record["data"] = data
        record["stamp"] = stamp

        line = (json.dumps(record, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")

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
        details: dict[str, Any],
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
        if not policy_uri or not (
            result is None or type(result) is bool or result == TRINARY_REPS[Unknown]
        ):
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

    execution_id = None
    record_ids = set()
    with Path(path).open("rb") as stream:
        for index, line in enumerate(stream):
            if not line.endswith(b"\n"):
                return
            record = json.loads(line, parse_constant=reject_constant)
            if not isinstance(record, dict):
                raise ValueError(f"Invalid journal record at line {index + 1}")  # noqa: TRY004 - malformed JSON record
            schema_version = record.get("schema_version")
            record_id_text = record.get("record_id")
            model_uri_text = record.get("model_uri")
            stamp = record.get("stamp")
            data = record.get("data")
            execution_uri_text = record.get("execution_id")
            if (
                type(schema_version) is not int
                or schema_version != SCHEMA_VERSION
                or not isinstance(record_id_text, str)
                or not isinstance(model_uri_text, str)
                or not isinstance(execution_uri_text, str)
                or not isinstance(stamp, (int, float))
                or data is not None
                and not isinstance(data, dict)
            ):
                raise ValueError(f"Invalid journal record at line {index + 1}")
            record_id = UUID(record_id_text)
            if str(record_id) != record_id_text or record_id in record_ids:
                raise ValueError("Invalid or duplicate record UUID")
            record_ids.add(record_id)
            model_uri = URIRef(model_uri_text)
            if not model_uri:
                raise ValueError("A record must reference a model URI")
            current_execution = URIRef(execution_uri_text)
            if not current_execution:
                raise ValueError("A record must reference an execution URI")
            if execution_id is not None and current_execution != execution_id:
                raise ValueError("A journal cannot contain multiple executions")
            execution_id = current_execution
            _validate_timestamp(stamp)
            record["record_id"] = record_id
            record["model_uri"] = model_uri
            record["execution_id"] = current_execution
            yield record
