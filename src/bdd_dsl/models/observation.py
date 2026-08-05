# SPDX-License-Identifier:  GPL-3.0-or-later
from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, Protocol

from rdf_utils.models.common import AttrLoaderProtocol, ModelBase
from rdf_utils.models.python import (
    URI_PY_TYPE_MODULE_ATTR,
    import_attr_from_model,
    load_py_module_attr,
)
from rdflib import Graph, URIRef
from trinary import Trinary, Unknown

from bdd_dsl.execution.scenario import ScenarioExecutionModel
from bdd_dsl.models.clauses import FluentClauseModel
from bdd_dsl.models.time_constraint import get_duration
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_OF_CLAUSE,
    URI_OBS_PRED_HAS_OBSERVATION,
    URI_OBS_PRED_OBSERVES_TARGET,
    URI_OBS_PRED_PROVIDER,
    URI_OBS_TYPE_POLICY,
    URI_TIME_PRED_AFTER_EVT,
    URI_TIME_PRED_BEFORE_EVT,
    URI_TIME_PRED_HRZN_SEC,
    URI_TIME_TYPE_AFTER_EVT,
    URI_TIME_TYPE_BEFORE_EVT,
    URI_TIME_TYPE_DURING,
)
from bdd_dsl.models.user_story import ScenarioVariantModel


@dataclass(frozen=True, slots=True)
class ObservationStamped:
    observation_uri: URIRef
    provider_uri: URIRef
    stamp: float
    value: Any


class TimestampedObservationProtocol(Protocol):
    def __call__(self, observation: Any, receipt_stamp: float) -> float: ...


@dataclass(frozen=True, slots=True)
class EntityObservation:
    entity_uri: URIRef
    value: Any


class EntityObservationMapperProtocol(Protocol):
    def __call__(self, observation: Any) -> list[EntityObservation]: ...


class ObservationPolicyEvaluatorProtocol(Protocol):
    def __call__(self, observations: list[ObservationStamped]) -> bool | Trinary: ...


@dataclass(frozen=True, slots=True)
class TrinaryStamped:
    stamp: float
    trinary: Trinary | bool


class TrinariesPolicyProtocol(Protocol):
    """Protocol for functions that load model attributes."""

    def __call__(self, trinaries: list[TrinaryStamped], **kwargs: Any) -> bool | Trinary: ...


def trin_policy_and(trinaries: list[TrinaryStamped], **kwargs: Any) -> bool | Trinary:
    if len(trinaries) == 0:
        return Unknown

    result = True
    for trin_st in trinaries:
        result &= trin_st.trinary

    return result


class ObsPolicyModel(ModelBase):
    trinary_timeline: list[TrinaryStamped]
    observation_uris: set[URIRef]
    observation_providers: dict[URIRef, URIRef]
    observation_targets: dict[URIRef, URIRef | None]
    evaluator: ObservationPolicyEvaluatorProtocol | None

    start_time: float | None
    end_time: float | None

    fluent_id: URIRef
    fluent_types: set[URIRef]
    duration_type: URIRef
    start_event: URIRef | None
    end_event: URIRef | None
    horizon: float | None

    def __init__(
        self,
        node_id: URIRef,
        graph: Graph,
        fluent_id: URIRef,
        fluent_types: set[URIRef],
        duration_type: URIRef,
        start_event: URIRef | None,
        end_event: URIRef | None,
        horizon: float | None,
    ) -> None:
        super().__init__(node_id=node_id, graph=graph)
        if URI_OBS_TYPE_POLICY not in self.types:
            raise ValueError(
                f"ObservationPolicy '{self.id}' does not have correct types: {self.types}"
            )
        self.fluent_id = fluent_id
        self.fluent_types = fluent_types
        self.duration_type = duration_type
        self.start_event = start_event
        self.end_event = end_event
        self.horizon = horizon

        self.trinary_timeline = []
        self.observation_uris = set()
        self.observation_providers = {}
        self.observation_targets = {}
        for obs_uri in graph.objects(subject=self.id, predicate=URI_OBS_PRED_HAS_OBSERVATION):
            if not isinstance(obs_uri, URIRef):
                raise TypeError(
                    f"ObservationPolicy '{self.id}' links to non-URI observation: {obs_uri}"
                )
            provider_uri = graph.value(subject=obs_uri, predicate=URI_OBS_PRED_PROVIDER, any=False)
            if not isinstance(provider_uri, URIRef):
                raise TypeError(f"Observation '{obs_uri}' has invalid provider: {provider_uri}")
            target_uri = graph.value(obs_uri, URI_OBS_PRED_OBSERVES_TARGET, any=False)
            if target_uri is not None and not isinstance(target_uri, URIRef):
                raise TypeError(f"Observation '{obs_uri}' has invalid target: {target_uri}")
            self.observation_uris.add(obs_uri)
            self.observation_providers[obs_uri] = provider_uri
            self.observation_targets[obs_uri] = target_uri

        self.evaluator = None
        if URI_PY_TYPE_MODULE_ATTR in self.types:
            load_py_module_attr(graph=graph, model=self, quiet=False)
            evaluator = import_attr_from_model(model=self)
            if not callable(evaluator):
                raise TypeError(f"ObservationPolicy '{self.id}' Python attribute is not callable")
            self.evaluator = evaluator

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

    def _discard_out_of_horizon_trin(self):
        """Clean up trinary queue for BeforeEvent type.

        Discard TrinaryStamped objects outside of the time horizon, calculated either
        from the end event or the latest TrinaryStamped instance.
        """
        if len(self.trinary_timeline) < 1 or self.end_time is not None:
            # if no trinary registered or timeline finished
            return

        assert self.horizon is not None, (
            f"{self.fluent_id}: _discard_out_of_horizon_trin called with no horizon specified for type: {self.duration_type}"
        )

        end_t = self.end_time
        if end_t is None:
            end_t = self.trinary_timeline[-1].stamp

        while len(self.trinary_timeline) > 0:
            first_trin_t = self.trinary_timeline[0].stamp
            start_t = end_t - self.horizon
            if first_trin_t > start_t:
                break
            self.trinary_timeline.pop(0)

    def add_trinary(self, trin_st: TrinaryStamped) -> tuple[bool, str]:
        if self.duration_type == URI_TIME_TYPE_BEFORE_EVT:
            # If end time is available then clause timeline should have finished
            if self.end_time is not None:
                # (Unlikely) add to record if trinary within time horizon
                assert self.start_time is not None
                if trin_st.stamp > self.start_time and trin_st.stamp < self.end_time:
                    self._insert_trin_stamped_in_order(trin_st)
                    return True, ""
                return False, "(before) finished and out of horizon"

            self._insert_trin_stamped_in_order(trin_st)

            self._discard_out_of_horizon_trin()
            return True, ""

        if self.duration_type == URI_TIME_TYPE_AFTER_EVT:
            # Not started
            if self.start_time is None:
                return False, "(after) not started"

            assert self.end_time is not None

            # Out of horizon
            if trin_st.stamp > self.end_time:
                return False, f"(after) out of horizon - {trin_st.stamp} > {self.end_time}"

            self._insert_trin_stamped_in_order(trin_st)
            return True, ""

        if self.duration_type == URI_TIME_TYPE_DURING:
            # Not started
            if self.start_time is None:
                return False, "(during) not started"

            # Out of horizon
            if self.end_time is not None and trin_st.stamp > self.end_time:
                return False, f"(during) out of horizon - {trin_st.stamp} > {self.end_time}"

            self._insert_trin_stamped_in_order(trin_st)
            return True, ""

        return False, "no matching type"

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
                self.start_time = self.end_time - self.horizon
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

        dur_spec = get_duration(constraint=fc)
        dur_type = None
        start_evt = None
        end_evt = None
        hrzn = None

        if URI_TIME_TYPE_DURING in fc.types:
            dur_type = URI_TIME_TYPE_DURING
            start_evt = dur_spec[URI_TIME_PRED_AFTER_EVT]
            end_evt = dur_spec[URI_TIME_PRED_BEFORE_EVT]
            hrzn = None

        elif URI_TIME_TYPE_AFTER_EVT in fc.types:
            dur_type = URI_TIME_TYPE_AFTER_EVT
            start_evt = dur_spec[URI_TIME_PRED_AFTER_EVT]
            end_evt = None
            hrzn = dur_spec[URI_TIME_PRED_HRZN_SEC]

        elif URI_TIME_TYPE_BEFORE_EVT in fc.types:
            dur_type = URI_TIME_TYPE_BEFORE_EVT
            start_evt = None
            end_evt = dur_spec[URI_TIME_PRED_BEFORE_EVT]
            hrzn = dur_spec[URI_TIME_PRED_HRZN_SEC]

        else:
            raise ValueError(
                "Unhandled duration types:\n" + "\n  ".join([uri.n3() for uri in fc.types])
            )

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
                duration_type=dur_type,
                start_event=start_evt,
                end_event=end_evt,
                horizon=hrzn,
            )


class ObservationManager:
    scenario_exec: ScenarioExecutionModel
    scr_start_time: float | None
    scr_end_time: float | None

    bhv_result: TrinaryStamped | None

    obs_policies: dict[URIRef, ObsPolicyModel]  # policy ID -> ObsPolicyModel
    providers: dict[URIRef, ModelBase]
    _fluent_policy_registry: dict[URIRef, set[URIRef]]  # fluent ID -> policy IDs
    observation_cache: dict[URIRef, ObservationStamped]
    _observation_policy_registry: dict[URIRef, URIRef]  # observation ID -> policy ID
    _provider_registry: dict[
        URIRef, tuple[TimestampedObservationProtocol | None, EntityObservationMapperProtocol | None]
    ]

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
        self.observation_cache = {}
        self._observation_policy_registry = {}
        self._provider_registry = {}

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
            if obs_pol.id not in self.scenario_exec.obs_policy_uris:
                # policy not explicitly included in execution model
                continue

            for loader in obs_loaders:
                loader(graph=graph, model=obs_pol)

            self._fluent_policy_registry[fc.id].add(obs_pol.id)
            for obs_uri in obs_pol.observation_uris:
                if obs_uri in self._observation_policy_registry:
                    raise ValueError(f"Observation already registered: '{obs_uri}'")
                self._observation_policy_registry[obs_uri] = obs_pol.id
            for provider_uri in set(obs_pol.observation_providers.values()):
                self.providers.setdefault(
                    provider_uri, ModelBase(node_id=provider_uri, graph=graph)
                )
            self._register_fluent_event(evt_uri=obs_pol.start_event, fc_id=fc.id)
            self._register_fluent_event(evt_uri=obs_pol.end_event, fc_id=fc.id)
            self.obs_policies[obs_pol.id] = obs_pol

    def register_provider(
        self,
        provider_uri: URIRef,
        timestamp_extractor: TimestampedObservationProtocol | None = None,
        entity_mapper: EntityObservationMapperProtocol | None = None,
    ) -> None:
        self._provider_registry[provider_uri] = (timestamp_extractor, entity_mapper)

    def bind_observation_targets(self, bindings: dict[URIRef, Any]) -> None:
        """Resolve template-variable targets for this scenario context."""
        for policy in self.obs_policies.values():
            for obs_uri, target_uri in policy.observation_targets.items():
                bound_target = bindings.get(target_uri)
                if bound_target is not None:
                    if not isinstance(bound_target, URIRef):
                        raise TypeError(
                            f"observation target '{target_uri}' is bound to non-URI {bound_target}"
                        )
                    policy.observation_targets[obs_uri] = bound_target

    def observation_targets_for_provider(self, provider_uri: URIRef) -> dict[URIRef, URIRef | None]:
        return {
            obs_uri: policy.observation_targets[obs_uri]
            for policy in self.obs_policies.values()
            for obs_uri, configured_provider in policy.observation_providers.items()
            if configured_provider == provider_uri
        }

    def update_provider_observation(
        self, provider_uri: URIRef, raw_value: Any, receipt_stamp: float
    ) -> dict[URIRef, tuple[bool, str]]:
        timestamp_extractor, entity_mapper = self._provider_registry.get(provider_uri, (None, None))
        stamp = (
            receipt_stamp
            if timestamp_extractor is None
            else timestamp_extractor(raw_value, receipt_stamp)
        )
        values: list[tuple[URIRef | None, Any]] = [(None, raw_value)]
        if entity_mapper is not None:
            for entity_obs in entity_mapper(raw_value):
                if not isinstance(entity_obs, EntityObservation):
                    raise TypeError(f"entity mapper for {provider_uri} returned {type(entity_obs)}")
                values.append((entity_obs.entity_uri, entity_obs.value))

        observations = []
        for obs_uri, policy_uri in self._observation_policy_registry.items():
            policy = self.obs_policies[policy_uri]
            if policy.observation_providers[obs_uri] != provider_uri:
                continue
            target_uri = policy.observation_targets[obs_uri]
            for entity_uri, value in values:
                if entity_uri == target_uri:
                    observations.append(ObservationStamped(obs_uri, provider_uri, stamp, value))
        return self.update_observations(observations)

    def update_bhv_result(self, trin_st: TrinaryStamped):
        self.bhv_result = trin_st

    def update_fpolicy_assertion(
        self, policy_uri: URIRef, trin_st: TrinaryStamped
    ) -> tuple[bool, str]:
        if policy_uri not in self.obs_policies:
            raise ValueError(f"ObservationPolicy not registered: '{policy_uri}'")

        return self.obs_policies[policy_uri].add_trinary(trin_st)

    def update_observations(
        self, observations: list[ObservationStamped]
    ) -> dict[URIRef, tuple[bool, str]]:
        """Atomically cache and evaluate each policy represented in a snapshot."""
        results: dict[URIRef, tuple[bool, str]] = {}
        obs_by_policy: dict[URIRef, list[ObservationStamped]] = {}
        stale_policies: set[URIRef] = set()
        for obs in observations:
            policy_uri = self._observation_policy_registry.get(obs.observation_uri)
            if policy_uri is None:
                raise ValueError(f"Observation not registered: '{obs.observation_uri}'")

            policy = self.obs_policies[policy_uri]
            provider_uri = policy.observation_providers.get(obs.observation_uri)
            if provider_uri is None:
                raise ValueError(
                    f"Observation '{obs.observation_uri}' is not configured for policy "
                    f"'{policy_uri}'"
                )
            if obs.provider_uri != provider_uri:
                raise ValueError(
                    f"Observation '{obs.observation_uri}' received from "
                    f"'{obs.provider_uri}', expected '{provider_uri}'"
                )
            obs_by_policy.setdefault(policy_uri, []).append(obs)
            cached = self.observation_cache.get(obs.observation_uri)
            if cached is not None and obs.stamp < cached.stamp:
                stale_policies.add(policy_uri)

        for policy_uri, policy_observations in obs_by_policy.items():
            if policy_uri in stale_policies:
                results[policy_uri] = (
                    False,
                    "(observation) older than cached sample",
                )
                continue

            for obs in policy_observations:
                self.observation_cache[obs.observation_uri] = obs

            policy = self.obs_policies[policy_uri]
            if policy.evaluator is None:
                results[policy_uri] = (False, "no evaluator")
                continue
            if any(uri not in self.observation_cache for uri in policy.observation_uris):
                results[policy_uri] = (True, "(observation) waiting for policy inputs")
                continue

            samples = [self.observation_cache[uri] for uri in policy.observation_uris]
            result = policy.evaluator(samples)
            results[policy_uri] = policy.add_trinary(
                TrinaryStamped(stamp=max(sample.stamp for sample in samples), trinary=result)
            )
        return results

    def on_event(self, evt_uri: URIRef, evt_t: float):
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
