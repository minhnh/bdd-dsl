# SPDX-License-Identifier:  GPL-3.0-or-later
import json
from rdflib import Graph, URIRef, RDF
from rdf_utils.uri import URL_SECORO_MM
from bdd_dsl.models.queries import Q_SIMULATED_OBJECT
from bdd_dsl.models.urirefs import (
    URI_ENV_PRED_HAS_OBJ_MODEL,
    URI_SIM_PRED_PATH,
    URI_SIM_PRED_HAS_CONFIG,
)


URL_MM_SIM_SHACL = f"{URL_SECORO_MM}/acceptance-criteria/bdd/simulation.shacl.ttl"


class ObjectModel(object):
    id: URIRef
    configs: dict
    model_id: URIRef
    model_types: set

    def __init__(self, graph: Graph, obj_id: URIRef):
        self.id = obj_id
        config_data = graph.value(subject=obj_id, predicate=URI_SIM_PRED_HAS_CONFIG)
        if config_data is None:
            self.configs = {}
        else:
            self.configs = json.loads(str(config_data))

        obj_models = list(graph.objects(subject=obj_id, predicate=URI_ENV_PRED_HAS_OBJ_MODEL))
        assert len(obj_models) == 1, f"expected 1 object model for '{obj_id}', got: {obj_models}"
        assert isinstance(obj_models[0], URIRef), f"'{obj_models[0]}' is not of type URIRef"
        self.model_id = obj_models[0]
        self.model_types = set(graph.objects(subject=self.model_id, predicate=RDF.type))


class ObjModelLoader(object):
    def __init__(self, graph: Graph):
        q_result = graph.query(Q_SIMULATED_OBJECT)
        assert (
            q_result.type == "CONSTRUCT" and q_result.graph is not None
        ), "querying simulated objects failed"

        self._sim_obj_graph = q_result.graph
        self._obj_models = {}  # Object URI -> ObjectModel instance

    def load_object_model(self, obj_id: URIRef) -> ObjectModel:
        if obj_id in self._obj_models:
            return self._obj_models[obj_id]

        obj_model = ObjectModel(graph=self._sim_obj_graph, obj_id=obj_id)
        self._obj_models[obj_id] = obj_model
        return obj_model


def get_path_of_node(graph: Graph, node_id: URIRef) -> str:
    path = graph.value(subject=node_id, predicate=URI_SIM_PRED_PATH)
    assert path is not None, f"node '{node_id}' has no edge '{URI_SIM_PRED_PATH}'"
    return str(path)
