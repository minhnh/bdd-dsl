# SPDX-License-Identifier:  GPL-3.0-or-later
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator, Mapping
from dataclasses import dataclass
from inspect import isclass
from math import dist, isclose
from numbers import Real
from typing import Any, Protocol

from rdf_utils.models.common import AttrLoaderProtocol, ModelBase, get_node_types
from rdf_utils.models.geom_coord import to_metres
from rdf_utils.models.python import (
    URI_PY_TYPE_MODULE_ATTR,
    import_attr_from_model,
    load_py_module_attr,
)
from rdf_utils.models.vocab import (
    URI_OBS_PRED_ENTITY_MAPPER,
    URI_OBS_PRED_HAS_EVALUATOR,
    URI_OBS_PRED_HAS_OBSERVATION,
    URI_OBS_PRED_OBSERVES_TARGET,
    URI_OBS_PRED_PROVIDER,
    URI_OBS_PRED_TIME_EXTRACTOR,
    URI_OBS_TYPE_DIRECT_TRINARY_POLICY,
    URI_OBS_TYPE_EVALUATED_POLICY,
    URI_OBS_TYPE_LINEAR_DISTANCE_EVALUATOR,
    URI_OBS_TYPE_OBSERVATION,
    URI_OBS_TYPE_POLICY,
    URI_QUDT_PRED_UNIT,
    URI_QUDT_PRED_VALUE,
    URI_TIME_PRED_AFTER_EVT,
    URI_TIME_PRED_BEFORE_EVT,
    URI_TIME_PRED_HRZN_SEC,
    URI_TIME_TYPE_AFTER_EVT,
    URI_TIME_TYPE_BEFORE_EVT,
    URI_TIME_TYPE_DURING,
)
from rdflib import RDF, Graph, Literal, URIRef
from scene_dsl.rdf_parser.scenex import SceneInstanceModel
from trinary import Trinary, Unknown

from bdd_dsl.execution.scenario import ScenarioExecutionModel
from bdd_dsl.models.clauses import FluentClauseModel
from bdd_dsl.models.time_constraint import get_duration, process_time_constraint_model
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_HAS_STRING_ENTITY_MAPPING,
    URI_BDD_PRED_MAPPED_ENTITY,
    URI_BDD_PRED_OF_CLAUSE,
    URI_BDD_PRED_STRING_VALUE,
    URI_BDD_TYPE_STRING_ENTITY_MAPPER,
    URI_BDD_TYPE_STRING_ENTITY_MAPPING,
    URI_BDD_TYPE_VARIABLE,
    URI_CSTR_PRED_HAS_CONSTRAINT,
    URI_CSTR_PRED_LOWER_THRESHOLD,
    URI_CSTR_PRED_REFERENCE_VALUE,
    URI_CSTR_PRED_THRESHOLD,
    URI_CSTR_PRED_TOLERANCE,
    URI_CSTR_PRED_UPPER_THRESHOLD,
    URI_CSTR_TYPE_BILATERAL,
    URI_CSTR_TYPE_EQUALITY,
    URI_CSTR_TYPE_GREATER_THAN,
    URI_CSTR_TYPE_LESS_THAN,
    URI_GEOM_PRED_BETWEEN_ENTITIES,
)
from bdd_dsl.models.user_story import ScenarioVariantModel


@dataclass(frozen=True, slots=True)
class ObservationStamped:
    """A normalized value for one policy-local observation input."""

    observation_uri: URIRef
    provider_uri: URIRef
    stamp: float
    value: Any


class TimestampedObservationProtocol(Protocol):
    """Extract a source timestamp, falling back to the ingress receipt timestamp."""

    def __call__(self, observation: Any, receipt_stamp: float) -> float: ...


@dataclass(frozen=True, slots=True)
class EntityObservation:
    entity_uri: URIRef
    value: Any


class EntityObservationMapperProtocol(Protocol):
    """Map a raw provider message using the active scenario scene."""

    def __call__(
        self,
        observation: Any,
        scene_instance: SceneInstanceModel,
        targets: list[URIRef],
    ) -> list[EntityObservation]: ...


def read_string_entity_mappings(
    graph: Graph,
    owner_uri: URIRef,
    variable_values: Mapping[URIRef, Any] | None = None,
) -> list[tuple[str, URIRef]]:
    mappings = []
    for mapping_uri in graph.objects(owner_uri, URI_BDD_PRED_HAS_STRING_ENTITY_MAPPING):
        string = graph.value(mapping_uri, URI_BDD_PRED_STRING_VALUE, any=False)
        entity = graph.value(mapping_uri, URI_BDD_PRED_MAPPED_ENTITY, any=False)
        if (
            (mapping_uri, RDF.type, URI_BDD_TYPE_STRING_ENTITY_MAPPING) not in graph
            or string is None
            or not isinstance(entity, URIRef)
        ):
            raise ValueError(f"StringEntityMapping {mapping_uri!r} is invalid")
        is_variable = (entity, RDF.type, URI_BDD_TYPE_VARIABLE) in graph
        if variable_values is not None:
            if is_variable and entity not in variable_values:
                raise ValueError(f"StringEntityMapping {mapping_uri!r} has an unbound variable")
            entity = variable_values.get(entity, entity)
            if not isinstance(entity, URIRef):
                raise TypeError(
                    f"StringEntityMapping {mapping_uri!r} resolved to non-URI {entity!r}"
                )
        mappings.append((str(string), entity))
    return mappings


class StringEntityMapper(ModelBase, EntityObservationMapperProtocol):
    def __init__(self, mapper_id: URIRef, graph: Graph) -> None:
        super().__init__(node_id=mapper_id, graph=graph)

        if URI_BDD_TYPE_STRING_ENTITY_MAPPER not in self.types:
            raise TypeError(f"StringEntityMapper '{self.id}' has incorrect types: {self.types}")
        self._graph = graph
        self._entity_by_string = dict(read_string_entity_mappings(graph, self.id))

    def bind_variable_values(self, variable_values: Mapping[URIRef, Any]) -> None:
        self._entity_by_string = dict(
            read_string_entity_mappings(self._graph, self.id, variable_values)
        )

    def __call__(
        self,
        observation: Any,
        scene_instance: SceneInstanceModel,
        targets: list[URIRef],
    ) -> list[EntityObservation]:
        del scene_instance
        if not isinstance(observation, Mapping):
            raise TypeError("StringEntityMapper requires a string-keyed mapping")
        target_set = set(targets)
        mapped = []
        for identifier, value in observation.items():
            if not isinstance(identifier, str):
                continue
            entity_uri = self._entity_by_string.get(identifier)
            if entity_uri in target_set:
                # set check already ensured that this is not None,
                # this is only for type check
                assert entity_uri is not None
                mapped.append(EntityObservation(entity_uri, value))
        return mapped


class ObservationModel(ModelBase):
    provider_id: URIRef
    time_extractor_id: URIRef
    # Manager-local target: starts as the RDF target and is replaced by its
    # scenario-variant binding before being passed to the entity mapper.
    target_id: URIRef | None
    entity_mapper_id: URIRef | None
    time_extractor: TimestampedObservationProtocol
    entity_mapper: EntityObservationMapperProtocol | None

    def __init__(self, obs_id: URIRef, graph: Graph) -> None:
        super().__init__(node_id=obs_id, graph=graph)
        if URI_OBS_TYPE_OBSERVATION not in self.types:
            raise ValueError(f"Observation '{self.id}' has incorrect types: {self.types}")

        provider_node = graph.value(self.id, URI_OBS_PRED_PROVIDER, any=False)
        if not isinstance(provider_node, URIRef):
            raise TypeError(f"Observation '{self.id}' has invalid provider: {provider_node}")
        self.provider_id = provider_node

        te_node = graph.value(self.id, URI_OBS_PRED_TIME_EXTRACTOR, any=False)
        if not isinstance(te_node, URIRef):
            raise TypeError(f"'{self}' has invalid time extractor: {te_node}")
        self.time_extractor_id = te_node

        self.target_id = _uri_or_none_value(graph, self.id, URI_OBS_PRED_OBSERVES_TARGET)
        self.entity_mapper_id = _uri_or_none_value(graph, self.id, URI_OBS_PRED_ENTITY_MAPPER)
        if self.target_id is not None and self.entity_mapper_id is None:
            raise ValueError(f"targeted '{self}' requires an entity mapper")

        self.time_extractor = _import_attr_from_graph(graph, self.time_extractor_id)
        if self.entity_mapper_id is None:
            self.entity_mapper = None
        elif URI_BDD_TYPE_STRING_ENTITY_MAPPER in get_node_types(
            graph=graph, node_id=self.entity_mapper_id
        ):
            self.entity_mapper = StringEntityMapper(self.entity_mapper_id, graph)
        else:
            self.entity_mapper = _import_attr_from_graph(graph, self.entity_mapper_id)


class ObservationPolicyEvaluator(ABC):
    """Base evaluator with a result for an empty observation set."""

    def __init__(
        self,
        default_result: tuple[bool | Trinary | None, str] = (
            Unknown,
            "no observations",
        ),
    ) -> None:
        self.default_result = default_result

    def evaluate(self, observations: list[ObservationStamped]) -> tuple[bool | Trinary | None, str]:
        if not observations:
            return self.default_result
        result = self._evaluate_samples(observations)
        if not isinstance(result, tuple) or len(result) != 2 or not isinstance(result[1], str):
            raise TypeError("observation evaluator must return (trinary, reason)")
        return result

    @abstractmethod
    def _evaluate_samples(
        self, observations: list[ObservationStamped]
    ) -> tuple[bool | Trinary | None, str]: ...


def _distance_value(graph: Graph, constraint: URIRef, predicate: URIRef) -> float:
    quantity = graph.value(constraint, predicate, any=False)
    if not isinstance(quantity, URIRef):
        raise TypeError(f"distance constraint {constraint} has invalid {predicate}: {quantity}")
    val_node = graph.value(quantity, URI_QUDT_PRED_VALUE, any=False)
    unit = graph.value(quantity, URI_QUDT_PRED_UNIT, any=False)
    if not isinstance(val_node, Literal) or not isinstance(unit, URIRef):
        raise TypeError(
            f"distance quantity {quantity} requires a literal value and unit, found: value={val_node}, unit={unit}"
        )
    value = val_node.toPython()
    if not isinstance(value, float):
        raise TypeError(f"distance quantity {quantity} requires a float value, found: {value}")
    return to_metres([float(value)], unit, quantity)[0]


class PositionXYZExtractorProtocol(Protocol):
    def __call__(self, observation: Any) -> tuple[float, ...] | None: ...


def _extract_position_xyz(observation: Any) -> tuple[float, ...] | None:
    if isinstance(observation, tuple):
        values = observation
    else:
        pose = getattr(observation, "pose", None)
        position = getattr(pose, "position", None)
        if position is None:
            return None
        values = (position.x, position.y, position.z)

    if len(values) != 3 or not all(
        isinstance(value, Real) and not isinstance(value, bool) for value in values
    ):
        return None
    return tuple(float(value) for value in values)


class LinearDistanceEvaluator(ObservationPolicyEvaluator):
    constraint_id: URIRef
    types: set[URIRef]
    constraint_values: tuple[float, ...]
    position_extractor: PositionXYZExtractorProtocol

    def __init__(
        self,
        graph: Graph,
        evaluator_id: URIRef,
        observations: set[URIRef],
        position_extractor: PositionXYZExtractorProtocol | None = None,
    ) -> None:
        super().__init__((Unknown, "linear distance expected 2 inputs, received 0"))

        if position_extractor is None:
            self.position_extractor = _extract_position_xyz
        else:
            self.position_extractor = position_extractor

        between = set(graph.objects(evaluator_id, URI_GEOM_PRED_BETWEEN_ENTITIES))
        if between != observations or len(between) != 2:
            raise ValueError(
                f"LinearDistanceEvaluator {evaluator_id} must reference exactly its two "
                "policy observations"
            )
        cstr_id = graph.value(evaluator_id, URI_CSTR_PRED_HAS_CONSTRAINT, any=False)
        if not isinstance(cstr_id, URIRef):
            raise TypeError(f"LinearDistanceEvaluator {evaluator_id} has invalid constraint")
        self.constraint_id = cstr_id
        self.types = get_node_types(graph=graph, node_id=cstr_id)

        if URI_CSTR_TYPE_LESS_THAN in self.types or URI_CSTR_TYPE_GREATER_THAN in self.types:
            self.constraint_values = (
                _distance_value(graph, self.constraint_id, URI_CSTR_PRED_THRESHOLD),
            )
        elif URI_CSTR_TYPE_BILATERAL in self.types:
            self.constraint_values = (
                _distance_value(graph, self.constraint_id, URI_CSTR_PRED_LOWER_THRESHOLD),
                _distance_value(graph, self.constraint_id, URI_CSTR_PRED_UPPER_THRESHOLD),
            )
        elif URI_CSTR_TYPE_EQUALITY in self.types:
            self.constraint_values = (
                _distance_value(graph, self.constraint_id, URI_CSTR_PRED_REFERENCE_VALUE),
                _distance_value(graph, self.constraint_id, URI_CSTR_PRED_TOLERANCE),
            )
        else:
            raise ValueError(f"unsupported linear distance constraint types: {self.types}")

    def _evaluate_samples(
        self, observations: list[ObservationStamped]
    ) -> tuple[bool | Trinary, str]:
        if len(observations) != 2:
            return (
                Unknown,
                f"linear distance expected 2 inputs, received {len(observations)}",
            )
        positions = []
        for i in range(2):
            position_obs = observations[i].value
            position = self.position_extractor(position_obs)
            if position is None:
                raise ValueError(f"can't extract position tuple from: {position_obs}")
            positions.append(position)
        measured = dist(*positions)

        if URI_CSTR_TYPE_LESS_THAN in self.types:
            result = measured < self.constraint_values[0] and not isclose(
                measured, self.constraint_values[0]
            )
            expectation = f"less than {self.constraint_values[0]:g} m"
        elif URI_CSTR_TYPE_GREATER_THAN in self.types:
            result = measured > self.constraint_values[0] and not isclose(
                measured, self.constraint_values[0]
            )
            expectation = f"greater than {self.constraint_values[0]:g} m"
        elif URI_CSTR_TYPE_BILATERAL in self.types:
            result = (
                measured > self.constraint_values[0] or isclose(measured, self.constraint_values[0])
            ) and (
                measured < self.constraint_values[1] or isclose(measured, self.constraint_values[1])
            )
            expectation = f"between {self.constraint_values[0]:g} m and {self.constraint_values[1]:g} m inclusive"
        else:
            reference, tolerance = self.constraint_values
            lower, upper = reference - tolerance, reference + tolerance
            result = (measured > lower or isclose(measured, lower)) and (
                measured < upper or isclose(measured, upper)
            )
            expectation = f"within {reference:g} m ± {tolerance:g} m ([{lower:g}, {upper:g}] m)"
        comparison = "is" if result else "is not"
        return result, f"linear distance {measured:g} m {comparison} {expectation}"


@dataclass(frozen=True, slots=True)
class TrinaryStamped:
    stamp: float
    trinary: Trinary | bool
    reason: str = ""


class TrinariesPolicyProtocol(Protocol):
    """Protocol for functions that load model attributes."""

    def __call__(
        self, trinaries: list[TrinaryStamped], **kwargs: Any
    ) -> tuple[bool | Trinary, str]: ...


def trin_policy_and(trinaries: list[TrinaryStamped], **kwargs: Any) -> tuple[bool | Trinary, str]:
    if len(trinaries) == 0:
        return Unknown, "no trinary assertions"

    result = True
    for trin_st in trinaries:
        result &= trin_st.trinary

    if result is False:
        reason = "at least one assertion is false"
    elif result is Unknown:
        reason = "at least one assertion is unknown"
    else:
        reason = "all assertions are true"
    return result, reason


def _uri_or_none_value(graph: Graph, subject_id: URIRef, predicate: URIRef) -> URIRef | None:
    val_node = graph.value(subject=subject_id, predicate=predicate, any=False)
    nm = graph.namespace_manager
    if val_node is not None and not isinstance(val_node, URIRef):
        raise TypeError(
            f"'{subject_id.n3(nm)}' links to non-URI node via {predicate.n3(nm)}: {val_node}"
        )
    return val_node


def _import_attr_from_graph(
    graph: Graph, node_id: URIRef, types: set[URIRef] | None = None, quiet: bool = False
) -> Any:
    model = ModelBase(node_id=node_id, graph=graph, types=types)
    load_py_module_attr(graph=graph, model=model, quiet=quiet)
    return import_attr_from_model(model=model)


class ObsPolicyModel(ModelBase):
    trinary_timeline: list[TrinaryStamped]
    observation_uris: set[URIRef]
    evaluator: ObservationPolicyEvaluator | None

    start_time: float | None
    end_time: float | None

    fluent_id: URIRef
    fluent_types: set[URIRef]
    duration_type: URIRef
    start_event: URIRef | None
    end_event: URIRef | None
    horizon: float | None
    evaluator_id: URIRef | None

    def __init__(
        self,
        node_id: URIRef,
        graph: Graph,
        fluent_id: URIRef,
        fluent_types: set[URIRef],
    ) -> None:
        super().__init__(node_id=node_id, graph=graph)
        if URI_OBS_TYPE_POLICY not in self.types:
            raise ValueError(
                f"ObservationPolicy '{self.id}' does not have correct types: {self.types}"
            )
        self.fluent_id = fluent_id
        self.fluent_types = fluent_types
        process_time_constraint_model(constraint=self, graph=graph)

        if URI_TIME_TYPE_DURING in self.types:
            self.duration_type = URI_TIME_TYPE_DURING
        elif URI_TIME_TYPE_AFTER_EVT in self.types:
            self.duration_type = URI_TIME_TYPE_AFTER_EVT
        elif URI_TIME_TYPE_BEFORE_EVT in self.types:
            self.duration_type = URI_TIME_TYPE_BEFORE_EVT
        else:
            raise ValueError(
                f"ObservationPolicy '{self.id}' has no supported temporal type: {self.types}"
            )

        if self.duration_type not in fluent_types:
            raise ValueError(
                f"ObservationPolicy '{self.id}' temporal type does not match fluent '{fluent_id}'"
            )

        duration = get_duration(constraint=self)
        self.start_event = duration.get(URI_TIME_PRED_AFTER_EVT)
        self.end_event = duration.get(URI_TIME_PRED_BEFORE_EVT)
        self.horizon = duration.get(URI_TIME_PRED_HRZN_SEC)

        if self.duration_type == URI_TIME_TYPE_DURING:
            if self.horizon is not None:
                raise ValueError(f"'{self}' must not specify a horizon for during")
        elif not isinstance(self.horizon, float):
            raise TypeError(
                f"ObservationPolicy '{self.id}' requires a horizon of type float for {self.duration_type}"
            )

        if self.duration_type == URI_TIME_TYPE_BEFORE_EVT:
            self.start_event = None
        elif self.duration_type == URI_TIME_TYPE_AFTER_EVT:
            self.end_event = None

        self.trinary_timeline = []
        self.observation_uris = set()
        for obs_uri in graph.objects(subject=self.id, predicate=URI_OBS_PRED_HAS_OBSERVATION):
            if not isinstance(obs_uri, URIRef):
                raise TypeError(
                    f"ObservationPolicy '{self.id}' links to non-URI observation: {obs_uri}"
                )
            self.observation_uris.add(obs_uri)
        self.evaluator_id = _uri_or_none_value(
            graph=graph, subject_id=self.id, predicate=URI_OBS_PRED_HAS_EVALUATOR
        )
        policy_adapters = (
            _uri_or_none_value(graph, self.id, URI_OBS_PRED_TIME_EXTRACTOR),
            _uri_or_none_value(graph, self.id, URI_OBS_PRED_ENTITY_MAPPER),
        )

        self.evaluator = None
        if URI_OBS_TYPE_DIRECT_TRINARY_POLICY in self.types:
            if self.observation_uris or any((*policy_adapters, self.evaluator_id)):
                raise ValueError(
                    f"TrinaryTopic policy '{self}' must not declare observations, adapters, or an evaluator"
                )
        elif URI_OBS_TYPE_EVALUATED_POLICY in self.types:
            if policy_adapters != (None, None):
                raise ValueError(f"Evaluated policy '{self}' must not declare adapters")
            if not self.observation_uris or self.evaluator_id is None:
                raise ValueError(
                    f"Evaluated policy '{self}' requires observations and an evaluator"
                )

            eval_types = get_node_types(graph=graph, node_id=self.evaluator_id)
            if URI_OBS_TYPE_LINEAR_DISTANCE_EVALUATOR in eval_types:
                self.evaluator = LinearDistanceEvaluator(
                    graph, self.evaluator_id, self.observation_uris
                )
            elif URI_PY_TYPE_MODULE_ATTR in eval_types:
                evaluator = _import_attr_from_graph(
                    graph=graph, node_id=self.evaluator_id, types=eval_types
                )
                if isclass(evaluator):
                    evaluator = evaluator()
                if not isinstance(evaluator, ObservationPolicyEvaluator):
                    raise TypeError(
                        f"ObservationPolicy '{self}' Python evaluator must be an ObservationPolicyEvaluator class"
                    )
                self.evaluator = evaluator
            else:
                raise TypeError(
                    f"ObservationPolicy '{self}' has unsupported evaluator types: {eval_types}"
                )
        else:
            raise ValueError(
                f"ObservationPolicy '{self}' has unsupported policy types: {self.types}"
            )

        self.start_time = None
        self.end_time = None

    def _insert_trin_stamped_in_order(self, trin_st: TrinaryStamped):
        # Find insertion point (from end)
        for i in range(len(self.trinary_timeline) - 1, -1, -1):
            if self.trinary_timeline[i].stamp < trin_st.stamp:
                self.trinary_timeline.insert(i + 1, trin_st)
                return

        # Insert at beginning if smallest
        self.trinary_timeline.insert(0, trin_st)

    def _discard_out_of_horizon_trin(self, reference_stamp: float | None = None):
        """Clean up trinary queue for BeforeEvent type.

        Discard TrinaryStamped objects outside of the time horizon relative to an
        explicit reference, the end event, or the latest TrinaryStamped instance.
        """
        if not self.trinary_timeline:
            # if no trinary registered
            return

        assert self.horizon is not None, (
            f"{self.fluent_id}: _discard_out_of_horizon_trin called with no horizon specified for type: {self.duration_type}"
        )

        end_t = reference_stamp if reference_stamp is not None else self.end_time
        if end_t is None:
            end_t = self.trinary_timeline[-1].stamp

        while len(self.trinary_timeline) > 0:
            first_trin_t = self.trinary_timeline[0].stamp
            start_t = end_t - self.horizon
            if first_trin_t >= start_t:
                break
            self.trinary_timeline.pop(0)

    def _check_time_constraint(self, stamp: float) -> tuple[bool, str]:
        """Check ``stamp`` against the closed interval of this time constraint."""
        if self.duration_type == URI_TIME_TYPE_BEFORE_EVT:
            if self.end_time is None:
                return True, ""
            assert self.start_time is not None
            if stamp < self.start_time or stamp > self.end_time:
                return False, (
                    f"(before) out of horizon - {stamp} not in [{self.start_time}, {self.end_time}]"
                )
            return True, ""

        if self.duration_type == URI_TIME_TYPE_AFTER_EVT:
            if self.start_time is None:
                return False, "(after) not started"
            assert self.end_time is not None
            if stamp < self.start_time or stamp > self.end_time:
                return False, (
                    f"(after) out of horizon - {stamp} not in [{self.start_time}, {self.end_time}]"
                )
            return True, ""

        if self.duration_type == URI_TIME_TYPE_DURING:
            if self.start_time is None:
                return False, "(during) not started"
            if stamp < self.start_time or (self.end_time is not None and stamp > self.end_time):
                end = self.end_time if self.end_time is not None else "open"
                return False, (
                    f"(during) out of horizon - {stamp} not in [{self.start_time}, {end}]"
                )
            return True, ""

        return False, "no matching type"

    def add_trinary(self, trin_st: TrinaryStamped) -> tuple[bool, str]:
        accepted, reason = self._check_time_constraint(trin_st.stamp)
        if not accepted:
            return accepted, reason

        self._insert_trin_stamped_in_order(trin_st)
        if self.duration_type == URI_TIME_TYPE_BEFORE_EVT:
            self._discard_out_of_horizon_trin()
        return True, ""

    def add_samples(
        self,
        samples: list[ObservationStamped],
        evaluation_stamp: float | None = None,
    ) -> tuple[bool, str]:
        if self.evaluator is None:
            return False, "no evaluator"
        if not samples and evaluation_stamp is None:
            return False, "no samples"
        for sample in samples:
            accepted, reason = self._check_time_constraint(sample.stamp)
            if not accepted:
                return accepted, reason
        trinary, reason = self.evaluator.evaluate(samples)
        if trinary is None:
            return True, reason
        return self.add_trinary(
            TrinaryStamped(
                stamp=(
                    evaluation_stamp
                    if evaluation_stamp is not None
                    else max(sample.stamp for sample in samples)
                ),
                trinary=trinary,
                reason=reason,
            )
        )

    def get_result(
        self,
        stamp: float,
        trinaries_policy: TrinariesPolicyProtocol,
    ) -> TrinaryStamped:
        if self.duration_type == URI_TIME_TYPE_BEFORE_EVT and self.end_time is None:
            self._discard_out_of_horizon_trin(stamp)

        if self.trinary_timeline:
            trinary, reason = trinaries_policy(self.trinary_timeline)
        elif self.evaluator is None:
            trinary, reason = Unknown, "no evaluator"
        else:
            trinary, reason = self.evaluator.evaluate([])
            trinary = Unknown if trinary is None else trinary
        return TrinaryStamped(stamp=stamp, trinary=trinary, reason=reason)

    def on_event(self, evt_uri: URIRef, evt_stamp: float):
        if evt_uri == self.start_event:
            if self.duration_type == URI_TIME_TYPE_AFTER_EVT:
                self.start_time = evt_stamp
                assert self.horizon is not None
                self.end_time = self.start_time + self.horizon
                return

            if self.duration_type == URI_TIME_TYPE_DURING:
                self.start_time = evt_stamp
                return

            raise ValueError(
                f"fluent {self.fluent_id}: matching start event '{self.start_event}' for wrong duration type: {self.duration_type}"
            )

        if evt_uri == self.end_event:
            if self.duration_type == URI_TIME_TYPE_BEFORE_EVT:
                self.end_time = evt_stamp
                assert self.horizon is not None
                # Time starts at 0 in simulation, so this avoids negative time
                self.start_time = max(0.0, self.end_time - self.horizon)
                self._discard_out_of_horizon_trin()
                return

            if self.duration_type == URI_TIME_TYPE_DURING:
                self.end_time = evt_stamp
                return

            raise ValueError(
                f"fluent {self.fluent_id}: matching end event '{self.end_event}' for wrong duration type: {self.duration_type}"
            )

    @classmethod
    def policies_for_fluent_clause(
        cls,
        graph: Graph,
        fc: FluentClauseModel,
    ) -> Generator[ObsPolicyModel, None, None]:

        for obs_pol_id in graph.subjects(predicate=URI_BDD_PRED_OF_CLAUSE, object=fc.id):
            if not isinstance(obs_pol_id, URIRef):
                raise TypeError(
                    f"Fluent '{fc.id}' is not linked via 'of-clause' to a ObservationPolicy URI: {obs_pol_id}"
                )

            yield ObsPolicyModel(
                node_id=obs_pol_id,
                graph=graph,
                fluent_id=fc.id,
                fluent_types=fc.types,
            )


class ObservationManager:
    """Route each provider snapshot into policy evaluators and fluent timelines.

    Observation adapters are loaded from observation RDF when building a scenario context. Feed
    raw provider messages through :meth:`update_provider_observation`; it extracts a
    timestamp, maps target-specific values, and evaluates each affected policy once.
    :meth:`update_fpolicy_assertion` remains the compatibility ingress for direct
    ``TrinaryStamped`` topic policies.
    """

    scenario_exec: ScenarioExecutionModel
    scr_start_time: float | None
    scr_end_time: float | None

    bhv_result: TrinaryStamped | None

    obs_policies: dict[URIRef, ObsPolicyModel]  # policy ID -> ObsPolicyModel
    providers: dict[URIRef, ModelBase]
    _fluent_policy_registry: dict[URIRef, set[URIRef]]  # fluent ID -> policy IDs
    observations: dict[URIRef, ObservationModel]
    _observation_policy_registry: dict[URIRef, set[URIRef]]
    _provider_observation_registry: dict[URIRef, set[URIRef]]

    event_timelines: dict[URIRef, list[float]]
    _fluent_event_registry: dict[URIRef, set[URIRef]]  # fluent ID -> event IDs

    def __init__(self, scr_exec: ScenarioExecutionModel) -> None:
        self.scenario_exec = scr_exec
        self.scr_start_time = None
        self.scr_end_time = None

        self.bhv_result = None

        self.obs_policies = {}
        self.providers = {}
        self._fluent_policy_registry = {}
        self.observations = {}
        self._observation_policy_registry = {}
        self._provider_observation_registry = {}

        self.event_timelines = {}
        self._fluent_event_registry = {}

    def _insert_evt_stamp_in_order(self, evt_uri: URIRef, evt_t: float):
        # Find insertion point (from end)
        for i in range(len(self.event_timelines[evt_uri]) - 1, -1, -1):
            if self.event_timelines[evt_uri][i] < evt_t:
                self.event_timelines[evt_uri].insert(i + 1, evt_t)
                return

        # Insert at beginning if smallest
        self.event_timelines[evt_uri].insert(0, evt_t)

    def _register_fluent_event(self, evt_uri: URIRef | None, fc_id: URIRef) -> None:
        if evt_uri is None:
            return

        if evt_uri not in self._fluent_event_registry:
            self._fluent_event_registry[evt_uri] = {fc_id}
            return

        self._fluent_event_registry[evt_uri].add(fc_id)

    def register_fluent_obs(
        self, graph: Graph, fc: FluentClauseModel, obs_loaders: list[AttrLoaderProtocol]
    ) -> None:
        """Register execution-selected observation policies for a fluent clause."""
        if fc.id in self._fluent_policy_registry:
            # Already registered
            return

        self._fluent_policy_registry[fc.id] = set()

        for obs_pol in ObsPolicyModel.policies_for_fluent_clause(
            graph=graph,
            fc=fc,
        ):
            if obs_pol.id in self.obs_policies:
                # policy already added.
                continue
            if self.scenario_exec.obs_policy_fluents.get(obs_pol.id) != fc.id:
                # policy not explicitly included in execution model
                continue

            for loader in obs_loaders:
                loader(graph=graph, model=obs_pol)

            self._fluent_policy_registry[fc.id].add(obs_pol.id)
            for obs_uri in obs_pol.observation_uris:
                observation = self.observations.get(obs_uri)
                if observation is None:
                    observation = ObservationModel(obs_id=obs_uri, graph=graph)
                    self.observations[obs_uri] = observation
                    self._provider_observation_registry.setdefault(
                        observation.provider_id, set()
                    ).add(obs_uri)
                self._observation_policy_registry.setdefault(obs_uri, set()).add(obs_pol.id)
                self.providers.setdefault(
                    observation.provider_id,
                    ModelBase(node_id=observation.provider_id, graph=graph),
                )
            self._register_fluent_event(evt_uri=obs_pol.start_event, fc_id=fc.id)
            self._register_fluent_event(evt_uri=obs_pol.end_event, fc_id=fc.id)
            self.obs_policies[obs_pol.id] = obs_pol

    def bind_observation_targets(self, bindings: dict[URIRef, Any]) -> None:
        """Resolve template-variable targets for this scenario context."""
        for observation in self.observations.values():
            if observation.target_id is None:
                continue
            bound_target = bindings.get(observation.target_id)
            if bound_target is not None:
                if not isinstance(bound_target, URIRef):
                    raise TypeError(
                        f"observation target '{observation.target_id}' is bound to non-URI "
                        f"{bound_target}"
                    )
                observation.target_id = bound_target
            if isinstance(observation.entity_mapper, StringEntityMapper):
                observation.entity_mapper.bind_variable_values(bindings)

    def observation_targets_for_provider(self, provider_uri: URIRef) -> dict[URIRef, URIRef | None]:
        """Return each configured observation and resolved target for ``provider_uri``."""
        return {
            obs_uri: self.observations[obs_uri].target_id
            for obs_uri in self._provider_observation_registry.get(provider_uri, ())
        }

    def update_provider_observation(
        self,
        provider_uri: URIRef,
        raw_value: Any,
        receipt_stamp: float,
    ) -> dict[URIRef, tuple[bool, str]]:
        """Normalize one raw provider value and route it to matching observations.

        Without an entity mapper, only targetless observations receive the raw value.
        """
        observations = []
        snapshot_stamps = []
        for obs_uri in self._provider_observation_registry.get(provider_uri, ()):
            observation = self.observations[obs_uri]
            stamp = observation.time_extractor(raw_value, receipt_stamp)
            snapshot_stamps.append(stamp)
            if observation.target_id is None:
                observations.append(ObservationStamped(obs_uri, provider_uri, stamp, raw_value))
                continue
            if observation.entity_mapper is None:
                raise ValueError(f"targeted observation '{obs_uri}' requires an entity mapper")
            for entity_obs in observation.entity_mapper(
                raw_value,
                self.scenario_exec.scene_instance,
                [observation.target_id],
            ):
                if not isinstance(entity_obs, EntityObservation):
                    raise TypeError(
                        f"entity mapper for observation '{obs_uri}' returned {type(entity_obs)}"
                    )
                if entity_obs.entity_uri == observation.target_id:
                    observations.append(
                        ObservationStamped(obs_uri, provider_uri, stamp, entity_obs.value)
                    )
        affected_policy_uris = {
            policy_uri
            for obs_uri in self._provider_observation_registry.get(provider_uri, ())
            for policy_uri in self._observation_policy_registry.get(obs_uri, ())
        }
        return self.update_observations(
            observations,
            affected_policy_uris=affected_policy_uris,
            evaluation_stamp=max(snapshot_stamps, default=receipt_stamp),
        )

    def update_bhv_result(self, trin_st: TrinaryStamped):
        """Record the behaviour result that closes the active scenario context."""
        self.bhv_result = trin_st

    @property
    def pending_end_deadline(self) -> float | None:
        """Return when the scenario may end, or None while it must remain active."""
        if self.scr_end_time is not None or self.bhv_result is None:
            return None

        deadline = self.bhv_result.stamp
        for policy in self.obs_policies.values():
            if policy.horizon is None:
                continue
            if policy.end_time is None:
                return None
            deadline = max(deadline, policy.end_time)
        return deadline

    def update_fpolicy_assertion(
        self, policy_uri: URIRef, trin_st: TrinaryStamped
    ) -> tuple[bool, str]:
        """Insert a direct trinary assertion for a legacy topic-backed policy."""
        if policy_uri not in self.obs_policies:
            raise ValueError(f"ObservationPolicy not registered: '{policy_uri}'")

        return self.obs_policies[policy_uri].add_trinary(trin_st)

    def update_observations(
        self,
        observations: list[ObservationStamped],
        *,
        affected_policy_uris: set[URIRef] | None = None,
        evaluation_stamp: float | None = None,
    ) -> dict[URIRef, tuple[bool, str]]:
        """Evaluate each represented policy from one observation snapshot.

        The returned dictionary maps each represented policy URI to an
        (accepted, reason) update outcome. The accepted flag reports whether the
        update was handled; it is not the policy's fluent trinary value.
        """
        results: dict[URIRef, tuple[bool, str]] = {}
        obs_by_policy: dict[URIRef, list[ObservationStamped]] = {
            policy_uri: [] for policy_uri in affected_policy_uris or ()
        }
        for obs in observations:
            policy_uris = self._observation_policy_registry.get(obs.observation_uri)
            if not policy_uris:
                raise ValueError(f"Observation not registered: '{obs.observation_uri}'")

            provider_uri = self.observations[obs.observation_uri].provider_id
            if obs.provider_uri != provider_uri:
                raise ValueError(
                    f"Observation '{obs.observation_uri}' received from "
                    f"'{obs.provider_uri}', expected '{provider_uri}'"
                )
            for policy_uri in policy_uris:
                obs_by_policy.setdefault(policy_uri, []).append(obs)

        for policy_uri, policy_observations in obs_by_policy.items():
            policy = self.obs_policies[policy_uri]
            results[policy_uri] = policy.add_samples(
                policy_observations,
                evaluation_stamp=evaluation_stamp if not policy_observations else None,
            )
        return results

    def on_event(self, evt_uri: URIRef, evt_t: float):
        """Record a scenario event and open or close affected fluent timelines."""
        if evt_uri not in self.event_timelines:
            self.event_timelines[evt_uri] = [evt_t]
        else:
            self._insert_evt_stamp_in_order(evt_uri=evt_uri, evt_t=evt_t)

        if evt_uri == self.scenario_exec.start_event:
            self.scr_start_time = evt_t
        elif evt_uri == self.scenario_exec.end_event:
            self.scr_end_time = evt_t

        if evt_uri not in self._fluent_event_registry:
            return

        for fc_uri in self._fluent_event_registry[evt_uri]:
            if fc_uri not in self._fluent_policy_registry:
                raise ValueError(f"On event {evt_uri}: No policy for fluent {fc_uri}")
            for obs_pol_id in self._fluent_policy_registry[fc_uri]:
                self.obs_policies[obs_pol_id].on_event(evt_uri=evt_uri, evt_stamp=evt_t)

    @classmethod
    def from_scenario_variant(
        cls,
        graph: Graph,
        scr_var: ScenarioVariantModel,
        bhv_loaders: list[AttrLoaderProtocol],
        obs_loaders: list[AttrLoaderProtocol],
    ) -> ObservationManager:
        """Build a manager for a scenario variant and register its fluent policies."""
        scr_exec = ScenarioExecutionModel(
            graph=graph,
            scr_var=scr_var,
            bhv_loaders=bhv_loaders,
        )
        obs_manager = ObservationManager(scr_exec=scr_exec)
        for fc in scr_var.fluent_clauses():
            obs_manager.register_fluent_obs(
                graph=graph,
                fc=fc,
                obs_loaders=obs_loaders,
            )
        return obs_manager
