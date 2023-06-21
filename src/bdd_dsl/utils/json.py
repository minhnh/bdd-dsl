import glob
from importlib import import_module
from typing import List, Tuple, Type, Union
import itertools
import json
from os.path import join
from pyld import jsonld
import py_trees as pt
import rdflib
from bdd_dsl.behaviours.actions import ActionWithEvents
from bdd_dsl.events.event_handler import EventHandler, SimpleEventLoop
from bdd_dsl import META_MODELs_PATH
from bdd_dsl.models.queries import (
    EVENT_LOOP_QUERY,
    BEHAVIOUR_TREE_QUERY,
    BDD_QUERY,
    Q_BT_SEQUENCE,
    Q_BT_PARALLEL,
    Q_OF_VARIABLE,
    Q_BDD_SCENARIO_VARIANT,
    Q_BDD_SCENARIO_VARIABLE,
    Q_PREDICATE,
)
from bdd_dsl.models.frames import (
    EVENT_LOOP_FRAME,
    BEHAVIOUR_TREE_FRAME,
    BDD_FRAME,
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
    FR_SCENARIO,
    FR_GIVEN,
    FR_THEN,
    FR_CLAUSES,
    FR_CRITERIA,
    FR_FLUENT_DATA,
    FR_VARIABLES,
    FR_VARIATIONS,
    FR_CONN,
)
from bdd_dsl.exception import BDDConstraintViolation
from bdd_dsl.utils.common import get_valid_var_name


def load_metamodels() -> rdflib.Graph:
    graph = rdflib.Graph()
    mm_files = glob.glob(join(META_MODELs_PATH, "*.json"))
    for mm_file in mm_files:
        graph.parse(mm_file, format="json-ld")
    return graph


def query_graph(graph: rdflib.Graph, query_str: str) -> dict:
    res = graph.query(query_str)
    res_json = json.loads(res.serialize(format="json-ld"))
    transformed_model = {"@graph": res_json}
    return transformed_model


def query_graph_with_file(graph: rdflib.Graph, query_file: str):
    with open(query_file) as infile:
        query_str = infile.read()
    return query_graph(graph, query_str)


def frame_model_with_file(model: dict, frame_file: str):
    with open(frame_file) as infile:
        frame_str = infile.read()
    frame_dict = json.loads(frame_str)
    return jsonld.frame(model, frame_dict)


def get_el_conn_event_names(graph: rdflib.Graph, el_conn_id: str) -> Union[List[str], None]:
    model = query_graph(graph, EVENT_LOOP_QUERY)
    framed_model = jsonld.frame(model, EVENT_LOOP_FRAME)

    # single match
    if FR_DATA not in framed_model:
        if FR_NAME not in framed_model or FR_EVENTS not in framed_model:
            raise ValueError(
                f"required fields '{FR_NAME}' or '{FR_EVENTS}' not in framed query result"
            )
        if framed_model[FR_NAME] != el_conn_id:
            return None
        return [event[FR_NAME] for event in framed_model[FR_EVENTS]]

    # multiple match
    for event_loop_data in framed_model[FR_DATA]:
        el_name = event_loop_data[FR_NAME]
        if el_conn_id != el_name:
            continue

        # first match
        return [event[FR_NAME] for event in event_loop_data[FR_EVENTS]]

    return None


def create_event_handler_from_data(
    el_data: dict, e_handler_cls: Type[EventHandler], e_handler_kwargs: dict
) -> EventHandler:
    """
    Create an event handler object from framed, dictionary-like data. Event handler must be an
    extension of EventDriven
    """
    event_names = [event[FR_NAME] for event in el_data[FR_EVENTS]]
    return e_handler_cls(el_data[FR_NAME], event_names, **e_handler_kwargs)


def create_event_handler_from_graph(
    graph: rdflib.Graph, e_handler_cls: Type[EventHandler], e_handler_kwargs: dict
) -> list:
    model = query_graph(graph, EVENT_LOOP_QUERY)
    framed_model = jsonld.frame(model, EVENT_LOOP_FRAME)

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


def get_bt_event_data_from_graph(graph: rdflib.Graph, bt_root_name: str = None) -> List[tuple]:
    bt_model = query_graph(graph, BEHAVIOUR_TREE_QUERY)
    bt_model_framed = jsonld.frame(bt_model, BEHAVIOUR_TREE_FRAME)

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
    bt_name: str = None,
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


def process_bdd_scenario_from_data(
    scenario_data: dict, conn_dict: dict, var_set: set, fluent_dict: dict
):
    scenario_name = scenario_data[FR_NAME]

    # variable connections
    if FR_CONN not in scenario_data:
        raise BDDConstraintViolation(
            f"{Q_BDD_SCENARIO_VARIANT} '{scenario_name}' has no connection"
        )
    for conn_data in scenario_data[FR_CONN]:
        if FR_VARIATIONS not in conn_data:
            continue
        conn_name = conn_data[FR_NAME]
        conn_dict[conn_name] = conn_data
        var_name = conn_data[Q_OF_VARIABLE][FR_NAME]
        if var_name in var_set:
            raise BDDConstraintViolation(
                f"multiple connections for {Q_BDD_SCENARIO_VARIABLE} '{var_name}'"
            )
        var_set.add(var_name)

    # fluent clauses
    clauses_data = []
    given_clauses_data = scenario_data[FR_SCENARIO][FR_GIVEN][FR_CLAUSES]
    if not isinstance(given_clauses_data, list):
        scenario_data[FR_SCENARIO][FR_GIVEN][FR_CLAUSES] = [given_clauses_data]
    clauses_data.extend(scenario_data[FR_SCENARIO][FR_GIVEN][FR_CLAUSES])

    then_clauses_data = scenario_data[FR_SCENARIO][FR_THEN][FR_CLAUSES]
    if not isinstance(then_clauses_data, list):
        scenario_data[FR_SCENARIO][FR_THEN][FR_CLAUSES] = [then_clauses_data]
    clauses_data.extend(scenario_data[FR_SCENARIO][FR_THEN][FR_CLAUSES])

    for clause_data in clauses_data:
        if Q_PREDICATE not in clause_data:
            continue
        clause_id = clause_data[FR_NAME]
        if clause_id in fluent_dict:
            continue
        fluent_dict[clause_id] = clause_data


def create_scenario_variations(scenario_data: dict, conn_dict: dict) -> Tuple[list, list]:
    var_names = []
    entities_list = []
    for conn_data in scenario_data[FR_CONN]:
        conn_name = conn_data[FR_NAME]
        var_name = conn_dict[conn_name][Q_OF_VARIABLE][FR_NAME]
        var_names.append(get_valid_var_name(var_name))
        var_entities = conn_dict[conn_name][FR_VARIATIONS]
        if isinstance(var_entities, dict):
            entities_list.append([var_entities[FR_NAME]])
        elif isinstance(var_entities, list):
            entities_list.append([ent_data[FR_NAME] for ent_data in var_entities])
        else:
            raise (
                ValueError(
                    "unhandled entity collection type '{}' for variable '{}'".format(
                        type(var_entities), var_name
                    )
                )
            )
    return var_names, list(itertools.product(*entities_list))


def process_bdd_us_from_data(us_data: dict):
    conn_dict = {}
    fluent_dict = {}
    var_set = set()
    if not isinstance(us_data[FR_CRITERIA], list):
        us_data[FR_CRITERIA] = [us_data[FR_CRITERIA]]

    # framing will include child concepts once for the same entity within one match,
    # so need to collect data for variable connections and fluent clauses to refer to later
    for scenario_data in us_data[FR_CRITERIA]:
        process_bdd_scenario_from_data(scenario_data, conn_dict, var_set, fluent_dict)

    for scenario_data in us_data[FR_CRITERIA]:
        # create variations for each scenario
        scenario_data[FR_VARIABLES], scenario_data[FR_VARIATIONS] = create_scenario_variations(
            scenario_data, conn_dict
        )

    us_data[FR_FLUENT_DATA] = fluent_dict
    return us_data


def process_bdd_us_from_graph(graph: rdflib.Graph) -> List:
    """Query and process all UserStory in the JSON-LD graph"""
    bdd_result = query_graph(graph, BDD_QUERY)
    model_framed = jsonld.frame(bdd_result, BDD_FRAME)
    if FR_DATA in model_framed:
        return [process_bdd_us_from_data(us_data) for us_data in model_framed[FR_DATA]]
    return [process_bdd_us_from_data(model_framed)]
