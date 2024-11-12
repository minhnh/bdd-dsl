# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Dict, Generator
from behave.model import Table
from behave import given
from rdf_utils.models.common import ModelBase, ModelLoader
from rdflib import Graph, URIRef
from behave.runner import Context
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
) -> Dict[URIRef, ModelBase]:
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
