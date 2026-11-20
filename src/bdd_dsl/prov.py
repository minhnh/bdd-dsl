# SPDX-License-Identifier: Apache-2.0
"""Scenario-scoped RDF provenance and synchronous JSONL evidence without ROS."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from math import isfinite
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from rdf_utils import DatasetFormat
from rdf_utils.collection import value_to_node
from rdf_utils.models.prov import add_entity, create_bundle
from rdf_utils.models.time import add_trs
from rdflib import RDF, Dataset, Graph, Literal, URIRef
from rdflib.namespace import PROV
from trinary import Trinary, Unknown

from bdd_dsl.models.observation import ObsDetailKey, ObsPolicyModel
from bdd_dsl.models.urirefs import URI_BDD_PRED_REF_VAR, URI_BDD_TYPE_VAR_ASSIGNMENT

SCHEMA_VERSION = 2
TRINARY_REPS = {True: True, False: False, Unknown: "unknown", None: None}


def _validate_timestamp(stamp: float) -> None:
    try:
        finite = not isinstance(stamp, bool) and isfinite(stamp)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError("A timestamp must be finite seconds")


class RecordingSession:
    """Own the shared recording dataset and persist it atomically.

    Parameters:
        output_dir: Directory receiving the execution dataset.
        agent_id: Software agent recording the executions.
        use_sim_time: True for simulation seconds, False for wall-clock Unix seconds.
        dataset_format: Dataset serialization format.
        config: Optional shared configuration snapshot; None omits it.
    """

    def __init__(
        self,
        output_dir: Path,
        agent_id: URIRef,
        *,
        use_sim_time: bool,
        dataset_format: DatasetFormat = DatasetFormat.JSON_LD,
        config: dict[str, Any] | None = None,
    ):
        # Setup provenance output directory
        self.output_dir = output_dir
        self.dataset_format = DatasetFormat(dataset_format)
        self.path = output_dir / f"execution.{self.dataset_format.extension}"
        for fmt in DatasetFormat:
            existing = output_dir / f"execution.{fmt.extension}"
            if existing.exists():
                raise FileExistsError(f"Provenance dataset already exists: {existing}")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Setup provenance dataset
        self.dataset = Dataset()
        self.agent_id = agent_id
        self.model_id = URIRef(uuid4().urn)
        self.prov_id = create_bundle(self.dataset, agent_id)
        self.dataset.graph(self.model_id)

        self.use_sim_time = use_sim_time
        self.config_id: URIRef | None = None
        if config is not None:
            encoded = json.dumps(config, allow_nan=False)
            self.config_id = add_entity(self.prov_bundle)
            self.prov_bundle.add((self.config_id, PROV.wasAttributedTo, agent_id))
            self.prov_bundle.add((self.config_id, PROV.value, Literal(encoded, datatype=RDF.JSON)))

    @property
    def model_graph(self) -> Graph:
        """Shared model graph in this session's dataset."""
        return self.dataset.graph(self.model_id)

    @property
    def prov_bundle(self) -> Graph:
        """Shared provenance bundle in this session's dataset."""
        return self.dataset.graph(self.prov_id)

    def save(self):
        temporary = self.path.with_name(self.path.name + ".tmp")
        self.dataset.serialize(temporary, format=self.dataset_format)
        os.replace(temporary, self.path)


class ScenarioExecRecorder:
    """Own an execution bundle and record JSONL evidence in its clock domain.

    Callers coordinate access, handle recording errors, and persist RDF updates with session.save().

    Parameters:
        path: new JSONL file; existing files are never overwritten
        context_id: scenario context UUID
        session: Shared dataset, software agent, model and clock settings.
    """

    def __init__(
        self,
        path: str | Path,
        context_id: UUID,
        session: RecordingSession,
    ) -> None:
        self.session = session
        self.path = Path(path)
        self.policy_configs: dict[URIRef, URIRef] = {}
        self._samples: dict[int, tuple[URIRef, float]] = {}

        self._closed = False
        self._failed = False
        self._stream = self.path.open("xb")

        self.dataset = session.dataset
        self.execution_id = URIRef(context_id.urn)
        self.bundle_id = create_bundle(self.dataset, session.agent_id)
        self.graph = self.dataset.graph(self.bundle_id)
        self.graph.add((self.execution_id, RDF.type, PROV.Activity))
        self.graph.add((self.execution_id, PROV.used, session.model_id))
        if session.config_id is not None:
            self.graph.add((self.execution_id, PROV.used, session.config_id))
        self.graph.add((self.execution_id, PROV.wasAssociatedWith, session.agent_id))
        self.dataset.default_graph.add((self.bundle_id, PROV.wasGeneratedBy, self.execution_id))

        self.trs_id = None
        if session.use_sim_time:
            self.trs_id = add_trs(self.graph)
            self.graph.add((self.execution_id, PROV.used, self.trs_id))

    def record_policy_eval(
        self,
        policy: ObsPolicyModel,
        stamp: float,
        trinary: bool | Trinary | None,
        details: dict[str, Any],
    ) -> None:
        sample_ids = details.get(ObsDetailKey.SAMPLE_IDS, [])
        stamps = details.get(ObsDetailKey.SAMPLE_STAMPS, [])
        uris = details.get(ObsDetailKey.OBS_IDS, [])
        for sample_id, sample_stamp, uri in zip(sample_ids, stamps, uris, strict=True):
            if not isinstance(uri, URIRef) or not uri:
                raise ValueError("Sample observation URI must be a nonempty URIRef")
            self.record_observation(sample_id, uri, sample_stamp)
        evidence = details
        if policy.id in self.policy_configs:
            evidence = {
                **details,
                ObsDetailKey.CONFIG_ID: self.policy_configs[policy.id],
            }
        result = TRINARY_REPS[trinary]
        self.record_evaluation(policy.id, stamp, result, evidence)

    def record_policy_config(self, policy: ObsPolicyModel) -> URIRef | None:
        """Snapshot evaluator settings and track the policy's current configuration.

        Parameters:
            policy: Observation policy whose effective evaluator settings are captured.

        Returns:
            Configuration URI, or None for a policy without an evaluator.
        """
        evaluator, evaluator_id = policy.evaluator, policy.evaluator_id
        if evaluator is None and evaluator_id is None:
            return None
        if evaluator is None or evaluator_id is None:
            missing = "evaluator" if evaluator is None else "evaluator_id"
            raise ValueError(f"Policy '{policy.id}' is missing {missing}")

        config_id = self.record_metadata(policy.id, evaluator.get_config())
        self.graph.add((config_id, PROV.wasDerivedFrom, evaluator_id))
        self.policy_configs[policy.id] = config_id
        return config_id

    def record_var_assignments(self, bindings: dict[URIRef, Any]) -> None:
        """Record resolved bindings as entities used by this execution.

        Parameters:
            bindings: Modeled variable URIs mapped to scalar, resource or ordered values.
        """

        for variable, value in bindings.items():
            if not isinstance(variable, URIRef):
                raise TypeError("Assignment variables must be URIRefs")
            encoded = value_to_node(self.graph, value)
            assignment = add_entity(self.graph)
            self.graph.add((assignment, RDF.type, URI_BDD_TYPE_VAR_ASSIGNMENT))
            self.graph.add((assignment, URI_BDD_PRED_REF_VAR, variable))
            self.graph.add((assignment, RDF.value, encoded))
            self.graph.add((self.execution_id, PROV.used, assignment))

    def record_metadata(self, model_uri: URIRef, data: dict[str, Any]) -> URIRef:
        """Add an immutable JSON snapshot to the execution bundle without writing JSONL.

        Parameters:
            model_uri: Model entity the metadata describes.
            data: JSON-compatible metadata dictionary.

        Returns:
            Metadata entity URI. The caller persists the dataset.
        """
        encoded = json.dumps(data, allow_nan=False)
        entity_id = add_entity(self.graph)
        self.graph.add((self.execution_id, PROV.used, entity_id))
        self.graph.add((entity_id, PROV.wasDerivedFrom, model_uri))
        self.graph.add((entity_id, PROV.value, Literal(encoded, datatype=RDF.JSON)))
        return entity_id

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
        references = details.get(ObsDetailKey.SAMPLE_IDS, ())
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
