# SPDX-License-Identifier:  GPL-3.0-or-later
import unittest
from typing import Any, Optional
from rdflib import URIRef, Graph, ConjunctiveGraph
import pyshacl
from rdf_utils.uri import URL_SECORO_M, URL_MM_PYTHON_SHACL
from rdf_utils.python import URI_PY_TYPE_MODULE_ATTR, URI_PY_PRED_ATTR_NAME, URI_PY_PRED_MODULE_NAME
from rdf_utils.resolver import install_resolver
from bdd_dsl.models.urirefs import URI_ENV_OF_OBJ
from bdd_dsl.simulation.common import (
    URI_SIM_TYPE_ISAAC_RES,
    URI_SIM_TYPE_SYS_RES,
    URL_MM_SIM_SHACL,
    ObjModelLoader,
    get_path_of_node,
)


MODEL_URLS = {
    f"{URL_SECORO_M}/acceptance-criteria/bdd/environments/secorolab.env.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/simulation/secorolab-isaac.sim.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/pickplace-secorolab-isaac.exec.json": "json-ld",
}
SHACL_URLS = {
    URL_MM_SIM_SHACL: "turtle",
    URL_MM_PYTHON_SHACL: "turtle",
}


class MockupObject(object):
    def __init__(self, obj_type: URIRef, obj_configs: Optional[dict], **kwargs: Any) -> None:
        self.obj_type = obj_type
        self.configs = obj_configs
        self.path = kwargs.get("path")
        self.module_name = kwargs.get("module_name")
        self.attr_name = kwargs.get("attr_name")


def load_obj_mockup(
    obj_res_g: Graph, obj_model_id: URIRef, obj_configs: Optional[dict], **kwargs: Any
) -> Any:
    for obj_model_type in obj_res_g.objects(subject=obj_model_id):
        assert isinstance(obj_model_type, URIRef)
        if obj_model_type == URI_SIM_TYPE_SYS_RES or obj_model_type == URI_SIM_TYPE_ISAAC_RES:
            path = get_path_of_node(obj_res_g, obj_model_id)
            return MockupObject(
                obj_type=obj_model_type, obj_configs=obj_configs, path=path, **kwargs
            )

        if obj_model_type == URI_PY_TYPE_MODULE_ATTR:
            module_name = obj_res_g.value(subject=obj_model_id, predicate=URI_PY_PRED_MODULE_NAME)
            attr_name = obj_res_g.value(subject=obj_model_id, predicate=URI_PY_PRED_ATTR_NAME)
            return MockupObject(
                obj_type=obj_model_type,
                obj_configs=obj_configs,
                module_name=module_name,
                attr_name=attr_name,
                **kwargs,
            )

    raise RuntimeError(f"unhandled type for object model '{obj_model_id}'")


class BDDSimTest(unittest.TestCase):
    def setUp(self):
        install_resolver()

    def test_exec(self):
        graph = ConjunctiveGraph()
        for url, fmt in MODEL_URLS.items():
            graph.parse(url, format=fmt)

        shacl_graph = ConjunctiveGraph()
        for mm_url, fmt in SHACL_URLS.items():
            shacl_graph.parse(mm_url, format=fmt)
        conforms, _, report_text = pyshacl.validate(
            graph,
            shacl_graph=shacl_graph,
            data_graph_format="json-ld",
            shacl_graph_format="ttl",
            inference="rdfs",
        )
        self.assertTrue(conforms, f"SHACL violation:\n{report_text}")

        obj_res_loader = ObjModelLoader(graph, obj_loader_func=load_obj_mockup)
        for _, obj_id in graph.subject_objects(predicate=URI_ENV_OF_OBJ):
            assert isinstance(obj_id, URIRef)
            obj_inst = obj_res_loader.load_object_model(obj_id)

            assert isinstance(obj_inst, MockupObject)
            if (
                obj_inst.obj_type == URI_SIM_TYPE_SYS_RES
                or obj_inst.obj_type == URI_SIM_TYPE_ISAAC_RES
            ):
                assert obj_inst.path is not None
            elif obj_inst.obj_type == URI_PY_TYPE_MODULE_ATTR:
                assert obj_inst.module_name is not None and obj_inst.attr_name is not None


if __name__ == "__main__":
    unittest.main()
