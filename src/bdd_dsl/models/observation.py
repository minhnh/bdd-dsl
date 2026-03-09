# SPDX-License-Identifier:  GPL-3.0-or-later
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from rdflib import Graph, URIRef
from rdflib.namespace import NamespaceManager
from trinary import Trinary, Unknown

from rdf_utils.models.common import AttrLoaderProtocol
from bdd_dsl.models.clauses import FluentClauseModel
from bdd_dsl.models.user_story import ScenarioVariantModel
from bdd_dsl.models.time_constraint import get_duration
from bdd_dsl.models.urirefs import (
    URI_TIME_PRED_AFTER_EVT,
    URI_TIME_PRED_BEFORE_EVT,
    URI_TIME_PRED_HRZN_SEC,
    URI_TIME_TYPE_AFTER_EVT,
    URI_TIME_TYPE_BEFORE_EVT,
    URI_TIME_TYPE_DURING,
)
from bdd_dsl.representation import ClauseRepBuilder, get_clause_role_rep


@dataclass
class TrinaryStamped:
    stamp: float
    trinary: Trinary | bool


class FluentTimeline(object):
    representation: str
    trinary_timeline: list[TrinaryStamped]

    start_time: Optional[float]
    end_time: Optional[float]

    fluent_id: URIRef
    fluent_types: set[URIRef]
    duration_type: URIRef
    start_event: Optional[URIRef]
    end_event: Optional[URIRef]
    horizon: Optional[float]

    def __init__(self, fc: FluentClauseModel, rep: str) -> None:
        self.fluent_id = fc.id
        self.fluent_types = fc.types
        self.representation = rep

        self.trinary_timeline = []

        self.start_time = None
        self.end_time = None

        dur_spec = get_duration(constraint=fc)

        if URI_TIME_TYPE_DURING in fc.types:
            self.duration_type = URI_TIME_TYPE_DURING
            self.start_event = dur_spec[URI_TIME_PRED_AFTER_EVT]
            self.end_event = dur_spec[URI_TIME_PRED_BEFORE_EVT]
            self.horizon = None

        elif URI_TIME_TYPE_AFTER_EVT in fc.types:
            self.duration_type = URI_TIME_TYPE_AFTER_EVT
            self.start_event = dur_spec[URI_TIME_PRED_AFTER_EVT]
            self.end_event = None
            self.horizon = dur_spec[URI_TIME_PRED_HRZN_SEC]

        elif URI_TIME_TYPE_BEFORE_EVT in fc.types:
            self.duration_type = URI_TIME_TYPE_BEFORE_EVT
            self.start_event = None
            self.end_event = dur_spec[URI_TIME_PRED_BEFORE_EVT]
            self.horizon = dur_spec[URI_TIME_PRED_HRZN_SEC]

        else:
            raise ValueError("Unhandled duration types:\n" + "\n  ".join(fc.types))

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


class ObservationManager(object):
    scr_rep: str
    scr_start_event: URIRef
    scr_end_event: URIRef
    scr_start_time: Optional[float]
    scr_end_time: Optional[float]

    bhv_result: Optional[TrinaryStamped]
    bhv_rep: str

    fluent_timelines: dict[URIRef, FluentTimeline]
    event_timelines: dict[URIRef, list[float]]
    _fluent_event_registry: dict[URIRef, set[URIRef]]
    _ns_manager: Optional[NamespaceManager]

    def __init__(
        self,
        scr_rep: str,
        scr_start_event: URIRef,
        scr_end_event: URIRef,
        bhv_rep: str,
        ns_manager: Optional[NamespaceManager] = None,
    ) -> None:
        self._ns_manager = ns_manager

        self.scr_rep = scr_rep
        self.scr_start_event = scr_start_event
        self.scr_end_event = scr_end_event
        self.scr_start_time = None
        self.scr_end_time = None

        self.bhv_rep = bhv_rep
        self.bhv_result = None

        self.fluent_timelines = {}
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
        self, graph: Graph, fc: FluentClauseModel, obs_loaders: list[AttrLoaderProtocol], rep: str
    ):
        if fc.id not in self.fluent_timelines:
            f_tl = FluentTimeline(fc=fc, rep=rep)
            self.fluent_timelines[fc.id] = f_tl
            self._register_fluent_event(evt_uri=f_tl.start_event, fc_id=fc.id)
            self._register_fluent_event(evt_uri=f_tl.end_event, fc_id=fc.id)

        for obs_ldr in obs_loaders:
            obs_ldr(graph=graph, model=fc)

    def update_bhv_result(self, trin_st: TrinaryStamped):
        self.bhv_result = trin_st

    def update_fpolicy_assertion(self, fc_uri: URIRef, trin_st: TrinaryStamped) -> tuple[bool, str]:
        assert fc_uri in self.fluent_timelines, f"No Timeline created for '{fc_uri}'"
        return self.fluent_timelines[fc_uri].add_trinary(trin_st)

    def on_event(self, evt_uri: URIRef, evt_t: float):
        if evt_uri not in self.event_timelines:
            self.event_timelines[evt_uri] = [evt_t]
        else:
            self._insert_evt_stamp_in_order(evt_uri=evt_uri, evt_t=evt_t)

        if evt_uri == self.scr_start_event:
            self.scr_start_time = evt_t
        elif evt_uri == self.scr_end_event:
            self.scr_end_time = evt_t

        if evt_uri not in self._fluent_event_registry:
            return

        for fc_uri in self._fluent_event_registry[evt_uri]:
            assert fc_uri in self.fluent_timelines
            self.fluent_timelines[fc_uri].on_event(evt_uri=evt_uri, evt_stamp=evt_t)

    @classmethod
    def from_scenario_variant(
        cls,
        graph: Graph,
        scr_var: ScenarioVariantModel,
        obs_loaders: list[AttrLoaderProtocol],
        clause_rep_builder: ClauseRepBuilder,
        val_dict: dict[URIRef, Any],
    ) -> ObservationManager:
        dur = get_duration(scr_var.tmpl)
        ns_manager = graph.namespace_manager
        assert URI_TIME_PRED_AFTER_EVT in dur and URI_TIME_PRED_BEFORE_EVT in dur, (
            f"ScenarioVariant '{scr_var.id.n3(ns_manager)}' does not have before/after event attributes"
        )

        scr_start_event = dur[URI_TIME_PRED_AFTER_EVT]
        scr_end_event = dur[URI_TIME_PRED_BEFORE_EVT]
        assert scr_start_event != scr_end_event, (
            f"ScenarioVariant '{scr_var.id.n3(ns_manager)}' has same start/end events: {scr_start_event}"
        )

        bhv_rep = clause_rep_builder.render_when_bhv_clause(
            clause=scr_var.when_bhv_model,
            val_dict=val_dict,
            ns_manager=ns_manager,
        )

        obs_manager = ObservationManager(
            scr_rep=scr_var.id.n3(ns_manager),
            scr_start_event=scr_start_event,
            scr_end_event=scr_end_event,
            bhv_rep=bhv_rep,
            ns_manager=ns_manager,
        )

        for fc in scr_var.fluent_clauses():
            fc_role = get_clause_role_rep(scenario=scr_var.scenario, clause=fc)
            fc_rep = clause_rep_builder.render_fluent_clause(
                role=fc_role, clause=fc, val_dict=val_dict, ns_manager=ns_manager
            )
            obs_manager.register_fluent_obs(graph=graph, fc=fc, obs_loaders=obs_loaders, rep=fc_rep)
        return obs_manager


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
