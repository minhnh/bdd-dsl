# SPDX-License-Identifier:  GPL-3.0-or-later
import json
from typing import Any, Dict
from rdflib import Graph, URIRef
from rdf_utils.uri import URL_SECORO_MM
from rdf_utils.models import ModelBase, ModelLoader
from bdd_dsl.models.queries import Q_SIMULATED_OBJECT
from bdd_dsl.models.urirefs import URI_SIM_PRED_HAS_CONFIG, URI_SIM_PRED_PATH, URI_SIM_TYPE_RES_PATH
from bdd_dsl.models.environment import ObjectModel


URL_MM_SIM_SHACL = f"{URL_SECORO_MM}/acceptance-criteria/bdd/simulation.shacl.ttl"


class ObjModelLoader(object):
    model_loader: ModelLoader
    _sim_obj_graph: Graph
    _obj_models: Dict[URIRef, ObjectModel]

    def __init__(self, graph: Graph):
        q_result = graph.query(Q_SIMULATED_OBJECT)
        assert (
            q_result.type == "CONSTRUCT" and q_result.graph is not None
        ), "querying simulated objects failed"

        self._sim_obj_graph = q_result.graph
        self._obj_models = {}  # Object URI -> ObjectModel instance

        self.model_loader = ModelLoader()

    def load_object_model(
        self, graph: Graph, obj_id: URIRef, override: bool = False, **kwargs: Any
    ) -> ObjectModel:
        if obj_id in self._obj_models and not override:
            return self._obj_models[obj_id]

        obj_model = ObjectModel(graph=self._sim_obj_graph, obj_id=obj_id)
        self.model_loader.load_attributes(graph=graph, model=obj_model, **kwargs)
        self._obj_models[obj_id] = obj_model
        return obj_model


def get_path_of_node(graph: Graph, node_id: URIRef) -> str:
    path = graph.value(subject=node_id, predicate=URI_SIM_PRED_PATH)
    assert path is not None, f"node '{node_id}' has no edge '{URI_SIM_PRED_PATH}'"
    return str(path)


def load_attr_path(graph: Graph, model: ModelBase, **kwargs: Any) -> None:
    if URI_SIM_TYPE_RES_PATH not in model.types:
        return

    path = graph.value(subject=model.id, predicate=URI_SIM_PRED_PATH)
    assert path is not None, f"node '{model.id}' has no edge '{URI_SIM_PRED_PATH}'"

    model.set_attr(key=URI_SIM_PRED_PATH, val=str(path))


def load_attr_has_config(graph: Graph, model: ModelBase, **kwargs: Any) -> None:
    serialized_configs = graph.value(subject=model.id, predicate=URI_SIM_PRED_HAS_CONFIG)
    if serialized_configs is None:
        config_data = {}
    else:
        config_data = json.loads(str(serialized_configs))

    model.set_attr(key=URI_SIM_PRED_HAS_CONFIG, val=config_data)
