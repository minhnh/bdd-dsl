# SPDX-License-Identifier:  GPL-3.0-or-later
from __future__ import annotations
import json
from typing import Any
from rdf_utils.models.common import ModelBase
from rdflib import Graph, URIRef
from rdf_utils.namespace import URL_SECORO_M, URL_SECORO_MM
from bdd_dsl.models.urirefs import (
    URI_EXEC_PRED_HAS_CONFIG,
    URI_EXEC_PRED_PATH,
    URI_EXEC_TYPE_RES_PATH,
)


URL_Q_SCENARIO_EXEC = f"{URL_SECORO_M}/acceptance-criteria/bdd/queries/scenario-execution.rq"
URL_MM_EXEC_SHACL = f"{URL_SECORO_MM}/acceptance-criteria/bdd/execution-context.shacl.ttl"


def get_path_of_node(graph: Graph, node_id: URIRef) -> str:
    path = graph.value(subject=node_id, predicate=URI_EXEC_PRED_PATH)
    assert path is not None, f"node '{node_id}' has no edge '{URI_EXEC_PRED_PATH}'"
    return str(path)


def load_attr_path(graph: Graph, model: ModelBase, **kwargs: Any) -> None:
    if URI_EXEC_TYPE_RES_PATH not in model.types:
        return

    path = graph.value(subject=model.id, predicate=URI_EXEC_PRED_PATH)
    assert path is not None, f"node '{model.id}' has no edge '{URI_EXEC_PRED_PATH}'"

    model.set_attr(key=URI_EXEC_PRED_PATH, val=str(path))


def load_attr_has_config(graph: Graph, model: ModelBase, **kwargs: Any) -> None:
    serialized_configs = graph.value(subject=model.id, predicate=URI_EXEC_PRED_HAS_CONFIG)
    if serialized_configs is None:
        config_data = {}
    else:
        config_data = json.loads(str(serialized_configs))

    model.set_attr(key=URI_EXEC_PRED_HAS_CONFIG, val=config_data)
