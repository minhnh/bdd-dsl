# SPDX-License-Identifier:  GPL-3.0-or-later
from importlib import import_module
from typing import List, Optional, Tuple, Type
from socket import _GLOBAL_DEFAULT_TIMEOUT
import json
from pyld import jsonld
import py_trees as pt
import rdflib
from rdf_utils.caching import read_file_and_cache, read_url_and_cache
from bdd_dsl.behaviours.actions import ActionWithEvents
from bdd_dsl.events.event_handler import EventHandler, SimpleEventLoop
from bdd_dsl.models.queries import (
    EVENT_LOOP_QUERY,
    BEHAVIOUR_TREE_QUERY,
    Q_BT_SEQUENCE,
    Q_BT_PARALLEL,
)
from bdd_dsl.models.frames import (
    EVENT_LOOP_FRAME,
    BEHAVIOUR_TREE_FRAME,
    FR_NAME,
    FR_DATA,
    FR_EVENTS,
    FR_SUBTREE,
    FR_TYPE,
    FR_CHILDREN,
    FR_START_E,
    FR_END_E,
    FR_IMPL_MODULE,
    FR_IMPL_CLASS,
    FR_IMPL_ARG_NAMES,
    FR_IMPL_ARG_VALS,
    FR_EL,
)


def query_graph(graph: rdflib.Graph, query_str: str) -> dict:
    res = graph.query(query_str)
    res_serialized = res.serialize(format="json-ld")
    assert res_serialized is not None

    res_json = json.loads(res_serialized)
    transformed_model = {"@graph": res_json}
    return transformed_model


def query_graph_with_file(graph: rdflib.Graph, query_file: str):
    query_str = read_file_and_cache(query_file)
    return query_graph(graph, query_str)


def query_graph_with_url(graph: rdflib.Graph, url: str, timeout=_GLOBAL_DEFAULT_TIMEOUT):
    query_str = read_url_and_cache(url, timeout=timeout)
    return query_graph(graph, query_str)


def frame_model_with_file(model: dict, frame_file: str) -> dict:
    frame_str = read_file_and_cache(frame_file)
    frame_dict = json.loads(frame_str)
    framed_res = jsonld.frame(model, frame_dict)
    assert isinstance(framed_res, dict)
    return framed_res


def frame_model_with_url(model: dict, url: str, timeout=_GLOBAL_DEFAULT_TIMEOUT) -> dict:
    frame_str = read_url_and_cache(url, timeout=timeout)
    frame_dict = json.loads(frame_str)
    framed_res = jsonld.frame(model, frame_dict)
    assert isinstance(framed_res, dict)
    return framed_res


def get_type_set(data: dict) -> set:
    assert FR_TYPE in data

    data_types = data[FR_TYPE]
    data_types_set = set()
    if isinstance(data_types, str):
        data_types_set.add(data_types)
    elif isinstance(data_types, list):
        for t in data_types:
            data_types_set.add(t)
    else:
        raise RuntimeError(f"unexpected type for '{FR_TYPE}' field: {type(data[FR_TYPE])}")
    return data_types_set


def create_event_handler_from_data(
    el_data: dict, e_handler_cls: Type[EventHandler], e_handler_kwargs: dict
) -> EventHandler:
    """Create an event handler object from framed, dictionary-like data.

    Event handler must be an extension of EventDriven
    """
    event_names = [event[FR_NAME] for event in el_data[FR_EVENTS]]
    return e_handler_cls(el_data[FR_NAME], event_names, **e_handler_kwargs)


def create_event_handler_from_graph(
    graph: rdflib.Graph, e_handler_cls: Type[EventHandler], e_handler_kwargs: dict
) -> list:
    model = query_graph(graph, EVENT_LOOP_QUERY)
    framed_model = jsonld.frame(model, EVENT_LOOP_FRAME)

    assert isinstance(framed_model, dict), f"unexpected type for framed model: {type(framed_model)}"

    if FR_DATA in framed_model:
        # multiple matches
        event_loops = []
        for event_loop_data in framed_model[FR_DATA]:
            event_loops.append(
                create_event_handler_from_data(event_loop_data, e_handler_cls, e_handler_kwargs)
            )
        return event_loops

    # single match
    return [create_event_handler_from_data(framed_model, e_handler_cls, e_handler_kwargs)]


def load_python_event_action(node_data: dict, event_handler: EventHandler):
    if FR_NAME not in node_data:
        raise ValueError(f"'{FR_NAME}' not found in node data")
    node_name = node_data[FR_NAME]

    for k in [FR_START_E, FR_END_E, FR_IMPL_MODULE, FR_IMPL_CLASS]:
        if k in node_data:
            continue
        raise ValueError(f"required key '{k}' not found in data for action '{node_name}'")

    action_cls = getattr(import_module(node_data[FR_IMPL_MODULE]), node_data[FR_IMPL_CLASS])
    if not issubclass(action_cls, ActionWithEvents):
        raise ValueError(
            f"'{action_cls.__name__}' is not a subclass of '{ActionWithEvents.__name__}'"
        )

    kwarg_dict = {}
    if FR_IMPL_ARG_NAMES in node_data and FR_IMPL_ARG_VALS in node_data:
        kwarg_names = node_data[FR_IMPL_ARG_NAMES]
        kwarg_vals = node_data[FR_IMPL_ARG_VALS]
        if not isinstance(kwarg_names, List):
            kwarg_names = [kwarg_names]
        if not isinstance(kwarg_vals, List):
            kwarg_vals = [kwarg_vals]

        if len(kwarg_names) != len(kwarg_vals):
            raise ValueError(f"argument count mismatch for action '{node_name}")
        for i in range(len(kwarg_names)):
            kwarg_dict[kwarg_names[i]] = kwarg_vals[i]
    return action_cls(
        node_name,
        event_handler,
        node_data[FR_START_E][FR_NAME],
        node_data[FR_END_E][FR_NAME],
        **kwarg_dict,
    )


def create_subtree_behaviours(
    subtree_data: dict, event_loop: EventHandler
) -> pt.composites.Composite:
    subtree_name = subtree_data[FR_NAME]
    composite_type = subtree_data[FR_TYPE]
    subtree_root = None
    if composite_type == Q_BT_SEQUENCE:
        subtree_root = pt.composites.Sequence(name=subtree_name, memory=True)
    elif composite_type == Q_BT_PARALLEL:
        # TODO: annotate policy on graph
        policy = pt.common.ParallelPolicy.SuccessOnAll(synchronise=True)
        subtree_root = pt.composites.Parallel(name=subtree_name, policy=policy)
    else:
        raise ValueError(f"composite type '{composite_type}' is not handled")

    for child_data in subtree_data[FR_CHILDREN]:
        if FR_CHILDREN in child_data:
            # recursive call TODO: confirm/check no cycle
            subtree_root.add_child(create_subtree_behaviours(child_data, event_loop))
            continue

        action = load_python_event_action(child_data, event_loop)
        subtree_root.add_child(action)

    return subtree_root


def get_bt_event_data_from_graph(
    graph: rdflib.Graph, bt_root_name: Optional[str] = None
) -> List[tuple]:
    bt_model = query_graph(graph, BEHAVIOUR_TREE_QUERY)
    bt_model_framed = jsonld.frame(bt_model, BEHAVIOUR_TREE_FRAME)

    assert isinstance(
        bt_model_framed, dict
    ), f"unexpected type for framed model: {type(bt_model_framed)}"

    if FR_DATA not in bt_model_framed:
        if bt_root_name is not None and bt_model_framed[FR_NAME] != bt_root_name:
            return []
        # single BT root
        return [(bt_model_framed[FR_EL], bt_model_framed[FR_SUBTREE])]

    ehs_and_bts = []
    for root_data in bt_model_framed[FR_DATA]:
        root_name = root_data[FR_NAME]
        if bt_root_name is not None and root_name != bt_root_name:
            # not the requested tree
            continue
        ehs_and_bts.append((root_data[FR_EL], root_data[FR_SUBTREE]))
    return ehs_and_bts


def create_bt_from_graph(
    graph: rdflib.Graph,
    bt_name: str,
    e_handler_cls: Type[EventHandler] = SimpleEventLoop,
    e_handler_kwargs: dict = {},
) -> List[Tuple]:
    e_data_and_bts = get_bt_event_data_from_graph(graph, bt_name)

    # multiple BT roots
    els_and_bts = []
    for e_data, subtree_data in e_data_and_bts:
        event_handler = create_event_handler_from_data(e_data, e_handler_cls, e_handler_kwargs)
        bt_root_node = create_subtree_behaviours(subtree_data, event_handler)
        els_and_bts.append((event_handler, bt_root_node))

    return els_and_bts
