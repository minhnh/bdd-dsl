# SPDX-License-Identifier:  GPL-3.0-or-later
import json
from typing import Optional, Protocol, Any
from rdflib import Graph, Namespace, URIRef
from rdf_utils.uri import URL_SECORO_MM, URL_SECORO_M
from rdf_utils.caching import read_url_and_cache


URI_MM_SIM = f"{URL_SECORO_MM}/simulation#"
URL_MM_SIM_SHACL = f"{URL_SECORO_MM}/acceptance-criteria/bdd/simulation.shacl.ttl"
URL_QUERY_SIM_OBJ = f"{URL_SECORO_M}/acceptance-criteria/bdd/queries/simulation-objects.rq"

NS_MM_SIM = Namespace(URI_MM_SIM)

URI_SIM_TYPE_SIM_OBJ = NS_MM_SIM["SimulatedObject"]
URI_SIM_TYPE_SYS_RES = NS_MM_SIM["SystemResource"]
URI_SIM_TYPE_ISAAC_RES = NS_MM_SIM["IsaacResource"]
URI_SIM_TYPE_OBJ_MODEL = NS_MM_SIM["ObjectModel"]

URI_SIM_PRED_OBJ_MODEL = NS_MM_SIM["object-model"]
URI_SIM_PRED_HAS_CONFIG = NS_MM_SIM["has-config"]
URI_SIM_PRED_PATH = NS_MM_SIM["path"]


class ObjLoaderProtocal(Protocol):
    """
    Protocol of methods for loading object models into simulation.

    :param obj_res_g: resulting graph after querying with ``URL_QUERY_SIM_OBJ``
    :param obj_model_id: URIRef of object model
    :param obj_configs: configurations of object models
    """

    def __call__(
        self, obj_res_g: Graph, obj_model_id: URIRef, obj_configs: Optional[dict], **kwargs: Any
    ) -> Any: ...


class ObjModelLoader(object):
    def __init__(self, g: Graph, obj_loader_func: ObjLoaderProtocal):
        g_query_str = read_url_and_cache(URL_QUERY_SIM_OBJ)
        q_result = g.query(g_query_str)
        assert q_result.type == "CONSTRUCT"
        assert q_result.graph is not None

        self._obj_resource_graph = q_result.graph
        self._obj_loader_func = obj_loader_func
        self._obj_to_model_cache = {}

    def load_object_model(self, obj_id: URIRef, **kwargs: Any) -> Any:
        if obj_id in self._obj_to_model_cache:
            obj_model_id = self._obj_to_model_cache[obj_id]
        else:
            obj_models = list(
                self._obj_resource_graph.objects(subject=obj_id, predicate=URI_SIM_PRED_OBJ_MODEL)
            )
            assert (
                len(obj_models) == 1
            ), f"expected 1 object model for '{obj_id}', got: {obj_models}"
            obj_model_id = obj_models[0]
            assert isinstance(obj_model_id, URIRef)
            self._obj_to_model_cache[obj_id] = obj_model_id

        obj_configs = get_config_of_node(self._obj_resource_graph, obj_id)
        return self._obj_loader_func(self._obj_resource_graph, obj_model_id, obj_configs, **kwargs)


def get_path_of_node(g: Graph, node_id: URIRef) -> str:
    path = g.value(subject=node_id, predicate=URI_SIM_PRED_PATH)
    assert path is not None, f"node '{node_id}' has no edge '{URI_SIM_PRED_PATH}'"
    return str(path)


def get_config_of_node(g: Graph, node_id: URIRef) -> Optional[dict]:
    config_data = g.value(subject=node_id, predicate=URI_SIM_PRED_HAS_CONFIG)

    if config_data is None:
        return None

    return json.loads(str(config_data))
