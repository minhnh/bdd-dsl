# SPDX-License-Identifier:  GPL-3.0-or-later
from enum import Enum
from typing import Any, Generator, Union
from ast import literal_eval
from behave.model import Table
from behave.runner import Context
from rdflib import Graph, URIRef
from rdflib.term import Node as RDFNode
from rdflib.namespace import NamespaceManager
from rdf_utils.uri import try_parse_n3_iterable, try_parse_n3_string
from rdf_utils.models.common import ModelBase, ModelLoader
from bdd_dsl.models.agent import AgentModel
from bdd_dsl.models.environment import ObjectModel
from bdd_dsl.models.user_story import SceneModel


PARAM_OBJ = "obj_str"
PARAM_WS = "ws_str"
PARAM_PICK_WS = "pick_ws_str"
PARAM_PLACE_WS = "place_ws_str"
PARAM_AGN = "agn_str"
PARAM_EVT = "evt_str"
CLAUSE_BG_OBJECTS = "a set of objects"
CLAUSE_BG_WORKSPACES = "a set of workspaces"
CLAUSE_BG_AGENTS = "a set of agents"
CLAUSE_FL_LOCATED_AT = f'"{{{PARAM_OBJ}}}" is located at "{{{PARAM_WS}}}"'
CLAUSE_TC_BEFORE_EVT = f'before event "{{{PARAM_EVT}}}"'
CLAUSE_TC_AFTER_EVT = f'after event "{{{PARAM_EVT}}}"'
CLAUSE_BHV_PICKPLACE = f'"{{{PARAM_AGN}}}" picks "{{{PARAM_OBJ}}}" from "{{{PARAM_PICK_WS}}}" and places it at "{{{PARAM_PLACE_WS}}}"'


def load_obj_models_from_table(
    table: Table, graph: Graph, scene: SceneModel
) -> Generator[ObjectModel, None, None]:
    """
    Load ObjectModel instances from a table of URIs in the behave Context,
    designed for the 'Given a set of objects' clause
    """
    for row in table:
        obj_id_str = row["name"]
        try:
            obj_uri = graph.namespace_manager.expand_curie(obj_id_str)
        except ValueError as e:
            raise RuntimeError(f"can't parse object URI '{obj_id_str}': {e}")

        yield scene.load_obj_model(obj_id=obj_uri, graph=graph)


def load_agn_models_from_table(
    table: Table, graph: Graph, scene: SceneModel
) -> Generator[AgentModel, None, None]:
    """
    Load AgentModel instances from a table of URIs in the behave Context,
    designed for the 'Given a set of agents' clause
    """
    for row in table:
        agn_id_str = row["name"]
        try:
            agn_uri = graph.namespace_manager.expand_curie(agn_id_str)
        except ValueError as e:
            raise RuntimeError(f"can't parse agent URI '{agn_id_str}': {e}")

        yield scene.load_agn_model(agent_id=agn_uri, graph=graph)


def load_ws_models_from_table(
    table: Table, graph: Graph, ws_model_loader: ModelLoader
) -> dict[URIRef, ModelBase]:
    workspace_models = {}
    for row in table:
        ws_id_str = row["name"]
        try:
            ws_uri = graph.namespace_manager.expand_curie(ws_id_str)
        except ValueError as e:
            raise RuntimeError(f"can't parse workspace URI '{ws_id_str}': {e}")

        ws_model = ModelBase(graph=graph, node_id=ws_uri)
        ws_model_loader.load_attributes(model=ws_model, graph=graph)
        workspace_models[ws_model.id] = ws_model

    return workspace_models


def given_ws_models(context: Context):
    assert context.table is not None, "no table added to context, expected a list of workspaces"
    assert context.model_graph is not None, "no 'model_graph' in context, expected an rdflib.Graph"
    assert (
        context.ws_model_loader is not None
    ), "no 'ws_model_loader' in context, expected a ModelLoader"
    context.workspaces = load_ws_models_from_table(
        table=context.table, graph=context.model_graph, ws_model_loader=context.ws_model_loader
    )


class ParamType(Enum):
    URI = 0
    EXISTS_SET = 1
    SET = 2


def parse_str_param(
    param_str: str, ns_manager: NamespaceManager
) -> tuple[ParamType, list[Union[RDFNode, str]]]:
    # ThereExists string representation: 'any of [set items]'
    if param_str.startswith("any of "):
        list_str = param_str.split("any of ")[1]
        try:
            n3_str_list = literal_eval(list_str)
        except SyntaxError as e:
            raise RuntimeError(f"unable to parse '{list_str}': {e}")

        assert isinstance(
            n3_str_list, list
        ), f"can't parse as a list (type={type(n3_str_list)}): {list_str}"

        n3_term_list = try_parse_n3_iterable(
            n3_str_iterable=n3_str_list, ns_manager=ns_manager, quiet=False
        )
        assert n3_term_list is not None, f"unable to parse N3 string list {n3_str_list}"
        return ParamType.EXISTS_SET, n3_term_list

    # regular list
    if param_str.startswith("["):
        try:
            n3_str_list = literal_eval(param_str)
        except SyntaxError as e:
            raise RuntimeError(f"unable to parse '{param_str}': {e}")

        assert isinstance(
            n3_str_list, list
        ), f"can't parse as a list (type={type(n3_str_list)}): {param_str}"

        n3_term_list = try_parse_n3_iterable(
            n3_str_iterable=n3_str_list, ns_manager=ns_manager, quiet=False
        )
        assert n3_term_list is not None, f"unable to parse N3 string list {n3_str_list}"
        return ParamType.SET, n3_term_list

    # N3 string
    n3_term = try_parse_n3_string(n3_str=param_str, ns_manager=ns_manager, quiet=False)
    assert n3_term is not None, f"can't parse N3 string: {param_str})"
    return ParamType.URI, [n3_term]


def load_str_params(param_names: list[str], **kwargs: Any) -> dict[str, str]:
    params = {}
    for param_name in param_names:
        param_str = kwargs.get(param_name, None)
        assert param_str is not None, f"no param '{param_name}' specified"
        params[param_name] = param_str

    return params
