# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Dict
from rdflib import Graph, URIRef
from behave.runner import Context
from bdd_dsl.simulation.common import ObjModelLoader, ObjectModel


def load_objects_models(
    context: Context, graph: Graph, obj_model_loader: ObjModelLoader
) -> Dict[URIRef, ObjectModel]:
    """
    Load ObjectModel instances from a table of URIs in the behave Context,
    designed for the 'Given a set of objects' clause
    """
    object_models = {}
    assert context.table is not None, "no table added to context, expected a list of objects"
    for row in context.table:
        obj_id_str = row["name"]
        try:
            obj_uri = graph.namespace_manager.expand_curie(obj_id_str)
        except ValueError as e:
            raise RuntimeError(f"can't parse object URI '{obj_id_str}': {e}")

        obj_model = obj_model_loader.load_object_model(obj_id=obj_uri, graph=graph)
        assert obj_model.id not in object_models, f"duplicate object ID found: {obj_model.id}"
        object_models[obj_model.id] = obj_model

    return object_models


def given_workspace_models(context: Context):
    ws_set = set()
    assert context.table is not None, "no table added to context, expected a list of workspaces"
    for row in context.table:
        ws_set.add(row["name"])

    context.workspaces = ws_set


def given_agent_models(context: Context):
    agent_set = set()
    assert context.table is not None, "no table added to context, expected a list of agents"
    for row in context.table:
        agent_set.add(row["name"])

    context.workspaces = agent_set
