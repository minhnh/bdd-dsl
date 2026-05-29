# SPDX-License-Identifier:  GPL-3.0-or-later
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Generator, Optional, Protocol
from trinary import Trinary, Unknown
from rdflib import Graph, URIRef
from rdf_utils.models.common import AttrLoaderProtocol, ModelBase
from bdd_dsl.execution.common import ScenarioExecutionModel
from bdd_dsl.models.time_constraint import get_duration
from bdd_dsl.models.user_story import ScenarioVariantModel
from bdd_dsl.models.clauses import FluentClauseModel
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_OF_CLAUSE,
    URI_OBS_TYPE_POLICY,
    URI_TIME_PRED_AFTER_EVT,
    URI_TIME_PRED_BEFORE_EVT,
    URI_TIME_PRED_HRZN_SEC,
    URI_TIME_TYPE_AFTER_EVT,
    URI_TIME_TYPE_BEFORE_EVT,
    URI_TIME_TYPE_DURING,
)


@dataclass
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

    start_time: Optional[float]
    end_time: Optional[float]

    fluent_id: URIRef
    fluent_types: set[URIRef]
    duration_type: URIRef
    start_event: Optional[URIRef]
    end_event: Optional[URIRef]
    horizon: Optional[float]

    def __init__(
        self,
        node_id: URIRef,
        graph: Graph,
        fluent_id: URIRef,
        fluent_types: set[URIRef],
        duration_type: URIRef,
        start_event: Optional[URIRef],
        end_event: Optional[URIRef],
        horizon: Optional[float],
    ) -> None:
        super().__init__(node_id=node_id, graph=graph)
        if URI_OBS_TYPE_POLICY not in self.types:
            raise ValueError(f"FluentImpl {self.id} does not have correct types: {self.types}")
        self.fluent_id = fluent_id
        self.fluent_types = fluent_types
        self.duration_type = duration_type
        self.start_event = start_event
        self.end_event = end_event
        self.horizon = horizon

        self.trinary_timeline = []

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
        obs_loaders: list[AttrLoaderProtocol],
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
                raise ValueError(f"Fluent '{fc.id}' does not link to an impl URIRef: {obs_pol_id}")

            obs_pol = ObsPolicyModel(
                node_id=obs_pol_id,
                graph=graph,
                fluent_id=fc.id,
                fluent_types=fc.types,
                duration_type=dur_type,
                start_event=start_evt,
                end_event=end_evt,
                horizon=hrzn,
            )

            for loader in obs_loaders:
                loader(graph=graph, model=obs_pol)

            yield obs_pol


class ObservationManager(object):
    scenario_exec: ScenarioExecutionModel
    scr_start_time: Optional[float]
    scr_end_time: Optional[float]

    bhv_result: Optional[TrinaryStamped]

    obs_policies: dict[URIRef, ObsPolicyModel]  # policy ID -> FluentImplModel
    _fluent_policy_registry: dict[URIRef, set[URIRef]]  # fluent ID -> policy IDs

    event_timelines: dict[URIRef, list[float]]
    _fluent_event_registry: dict[URIRef, set[URIRef]]  # fluent ID -> event IDs

    def __init__(self, scr_exec: ScenarioExecutionModel) -> None:
        self.scenario_exec = scr_exec
        self.scr_start_time = None
        self.scr_end_time = None

        self.bhv_result = None

        self.obs_policies = {}
        self._fluent_policy_registry = {}

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
            graph=graph, fc=fc, obs_loaders=obs_loaders
        ):
            if obs_pol.id in self.obs_policies:
                # policy already added.
                continue
            if obs_pol.id not in self.scenario_exec.obs_policy_uris:
                raise ValueError(
                    f"FluentImpl '{obs_pol.id}' not included in ScenarioExecution '{self.scenario_exec.id}'"
                )
            self._fluent_policy_registry[fc.id].add(obs_pol.id)
            self._register_fluent_event(evt_uri=obs_pol.start_event, fc_id=fc.id)
            self._register_fluent_event(evt_uri=obs_pol.end_event, fc_id=fc.id)
            self.obs_policies[obs_pol.id] = obs_pol

    def update_bhv_result(self, trin_st: TrinaryStamped):
        self.bhv_result = trin_st

    def update_fpolicy_assertion(
        self, policy_uri: URIRef, trin_st: TrinaryStamped
    ) -> tuple[bool, str]:
        if policy_uri not in self.obs_policies:
            raise ValueError(f"ObservationPolicy not registered: '{policy_uri}'")

        return self.obs_policies[policy_uri].add_trinary(trin_st)

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
