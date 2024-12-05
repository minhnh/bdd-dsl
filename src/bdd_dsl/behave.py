# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Generator, Union
from ast import literal_eval
from behave.model import Table
from behave import given
from behave.runner import Context
from rdf_utils.uri import try_expand_curie
from rdflib import Graph, URIRef
from rdflib.namespace import NamespaceManager
from rdf_utils.models.common import ModelBase, ModelLoader
from bdd_dsl.models.agent import AgentModel
from bdd_dsl.models.environment import ObjectModel
from bdd_dsl.models.user_story import SceneModel


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


@given("a set of workspaces")
def given_ws_models(context: Context):
    assert context.table is not None, "no table added to context, expected a list of workspaces"
    assert context.model_graph is not None, "no 'model_graph' in context, expected an rdflib.Graph"
    assert (
        context.ws_model_loader is not None
    ), "no 'ws_model_loader' in context, expected a ModelLoader"
    context.workspaces = load_ws_models_from_table(
        table=context.table, graph=context.model_graph, ws_model_loader=context.ws_model_loader
    )


def parse_uri_or_set(arg_str: str, ns_manager: NamespaceManager) -> Union[URIRef, list[URIRef]]:
    # ThereExists string representation: 'any of [set items]'
    if arg_str.startswith("any of "):
        list_str = arg_str.split("any of ")[1]
        try:
            uri_str_list = literal_eval(list_str)
        except SyntaxError as e:
            raise RuntimeError(f"unable to parse '{list_str}': {e}")

        assert isinstance(
            uri_str_list, list
        ), f"can't parse as a list (type={type(uri_str_list)}): {list_str}"

        uri_list = []
        for uri_str in uri_str_list:
            uri = try_expand_curie(curie_str=uri_str, ns_manager=ns_manager, quiet=False)
            assert uri is not None, f"can't parse as URI: {uri_str} (type={type(uri)})"
            uri_list.append(uri)

        return uri_list

    # shortened URI form
    uri = try_expand_curie(curie_str=arg_str, ns_manager=ns_manager, quiet=False)
    assert uri is not None, f"can't parse as URI: {arg_str} (type={type(uri)})"
    return uri
