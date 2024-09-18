# SPDX-License-Identifier:  GPL-3.0-or-later
import unittest
from rdflib import URIRef, ConjunctiveGraph
import pyshacl
from rdf_utils.uri import URL_SECORO_M, URL_MM_PYTHON_SHACL
from rdf_utils.python import URI_PY_TYPE_MODULE_ATTR, URI_PY_PRED_ATTR_NAME, URI_PY_PRED_MODULE_NAME
from rdf_utils.resolver import install_resolver
from bdd_dsl.models.urirefs import URI_ENV_PRED_OF_OBJ, URI_SIM_TYPE_SYS_RES
from bdd_dsl.simulation.common import (
    URL_MM_SIM_SHACL,
    ObjModelLoader,
    get_path_of_node,
    load_attr_has_config,
    load_attr_path,
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

        obj_res_loader = ObjModelLoader(graph)
        obj_res_loader.model_loader.register(load_attr_path)
        obj_res_loader.model_loader.register(load_attr_has_config)
        for _, obj_id in graph.subject_objects(predicate=URI_ENV_PRED_OF_OBJ):
            assert isinstance(obj_id, URIRef)
            obj_inst = obj_res_loader.load_object_model(obj_id=obj_id, graph=graph)

            if URI_SIM_TYPE_SYS_RES in obj_inst.model_types:
                assert len(obj_inst.model_type_to_id[URI_SIM_TYPE_SYS_RES]) == 1
                sys_res_model_id = list(obj_inst.model_type_to_id[URI_SIM_TYPE_SYS_RES])[0]
                _ = get_path_of_node(graph=graph, node_id=sys_res_model_id)

            elif URI_PY_TYPE_MODULE_ATTR in obj_inst.model_types:
                assert len(obj_inst.model_type_to_id[URI_PY_TYPE_MODULE_ATTR]) == 1
                py_attr_model_id = list(obj_inst.model_type_to_id[URI_PY_TYPE_MODULE_ATTR])[0]
                module_name = graph.value(
                    subject=py_attr_model_id, predicate=URI_PY_PRED_MODULE_NAME
                )
                attr_name = graph.value(subject=py_attr_model_id, predicate=URI_PY_PRED_ATTR_NAME)
                assert module_name is not None and attr_name is not None


if __name__ == "__main__":
    unittest.main()
