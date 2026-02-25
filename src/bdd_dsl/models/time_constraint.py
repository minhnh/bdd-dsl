# SPDX-License-Identifier:  GPL-3.0-or-later
from rdflib import Graph, Literal, URIRef
from rdf_utils.models.common import ModelBase
from bdd_dsl.models.urirefs import (
    URI_TIME_PRED_AFTER_EVT,
    URI_TIME_PRED_BEFORE_EVT,
    URI_TIME_PRED_HRZN_SEC,
    URI_TIME_TYPE_AFTER_EVT,
    URI_TIME_TYPE_BEFORE_EVT,
    URI_TIME_TYPE_DURING,
)


def process_time_constraint_model(constraint: ModelBase, graph: Graph) -> None:
    hrzn_secs = graph.value(subject=constraint.id, predicate=URI_TIME_PRED_HRZN_SEC, any=False)
    if isinstance(hrzn_secs, Literal):
        hrzn_float = hrzn_secs.toPython()
        assert isinstance(
            hrzn_float, float
        ), f"Horizon seconds not a float ({type(hrzn_float)}): {hrzn_float}"
        constraint.set_attr(key=URI_TIME_PRED_HRZN_SEC, val=hrzn_float)

    if URI_TIME_TYPE_BEFORE_EVT in constraint.types:
        before_evt_uri = graph.value(
            subject=constraint.id, predicate=URI_TIME_PRED_BEFORE_EVT, any=False
        )
        assert isinstance(
            before_evt_uri, URIRef
        ), f"BeforeEvent TC '{constraint.id}' missing 'before-event' pred to URI: {before_evt_uri}"
        constraint.set_attr(key=URI_TIME_PRED_BEFORE_EVT, val=before_evt_uri)
        return

    if URI_TIME_TYPE_AFTER_EVT in constraint.types:
        after_evt_uri = graph.value(
            subject=constraint.id, predicate=URI_TIME_PRED_AFTER_EVT, any=False
        )
        assert isinstance(
            after_evt_uri, URIRef
        ), f"AfterEvent TC '{constraint.id}' missing 'after-event' pred to URI: {after_evt_uri}"
        constraint.set_attr(key=URI_TIME_PRED_AFTER_EVT, val=after_evt_uri)
        return

    if URI_TIME_TYPE_DURING in constraint.types:
        before_evt_uri = graph.value(
            subject=constraint.id, predicate=URI_TIME_PRED_BEFORE_EVT, any=False
        )
        assert isinstance(
            before_evt_uri, URIRef
        ), f"DuringEvents TC '{constraint.id}' missing 'before-event' pred to URI: {before_evt_uri}"
        constraint.set_attr(key=URI_TIME_PRED_BEFORE_EVT, val=before_evt_uri)

        after_evt_uri = graph.value(
            subject=constraint.id, predicate=URI_TIME_PRED_AFTER_EVT, any=False
        )
        assert isinstance(
            after_evt_uri, URIRef
        ), f"DuringEvents TC '{constraint.id}' missing 'after-event' pred to URI: {after_evt_uri}"
        constraint.set_attr(key=URI_TIME_PRED_AFTER_EVT, val=after_evt_uri)
        return

    raise RuntimeError(f"unhandled types for time constraint '{constraint.id}': {constraint.types}")


def get_duration(constraint: ModelBase) -> dict:
    start_evt_uri = constraint.get_attr(key=URI_TIME_PRED_AFTER_EVT)
    end_evt_uri = constraint.get_attr(key=URI_TIME_PRED_BEFORE_EVT)
    hrzn_secs = constraint.get_attr(key=URI_TIME_PRED_HRZN_SEC)

    if URI_TIME_TYPE_DURING in constraint.types:
        assert (
            isinstance(start_evt_uri, URIRef) and isinstance(end_evt_uri, URIRef)
        ), f"DuringEvents '{constraint.id}' has invalid attrs: start={start_evt_uri}, end={end_evt_uri}"
        return {
            URI_TIME_PRED_AFTER_EVT: start_evt_uri,
            URI_TIME_PRED_BEFORE_EVT: end_evt_uri,
        }

    if URI_TIME_TYPE_AFTER_EVT in constraint.types:
        assert (
            isinstance(start_evt_uri, URIRef) and isinstance(hrzn_secs, float)
        ), f"AfterEvent '{constraint.id}' has invalid attrs: start={start_evt_uri}, horizon={hrzn_secs}"
        return {
            URI_TIME_PRED_AFTER_EVT: start_evt_uri,
            URI_TIME_PRED_HRZN_SEC: hrzn_secs,
        }

    if URI_TIME_TYPE_BEFORE_EVT in constraint.types:
        assert (
            isinstance(end_evt_uri, URIRef) and isinstance(hrzn_secs, float)
        ), f"BeforeEvent '{constraint.id}' has invalid attrs: end={end_evt_uri}, horizon={hrzn_secs}"
        return {
            URI_TIME_PRED_BEFORE_EVT: end_evt_uri,
            URI_TIME_PRED_HRZN_SEC: hrzn_secs,
        }

    raise RuntimeError(f"unhandled types for time constraint '{constraint.id}': {constraint.types}")
