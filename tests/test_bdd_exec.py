# SPDX-License-Identifier:  GPL-3.0-or-later
import unittest
from urllib.request import HTTPError
from rdflib import Dataset
from rdf_utils.uri import URL_SECORO_M, URL_MM_PYTHON_SHACL
from rdf_utils.models.python import (
    URI_PY_TYPE_MODULE_ATTR,
    URI_PY_PRED_ATTR_NAME,
    URI_PY_PRED_MODULE_NAME,
    load_py_module_attr,
)
from rdf_utils.resolver import install_resolver
from rdf_utils.constraints import check_shacl_constraints
from bdd_dsl.models.agent import AgentModel
from bdd_dsl.models.environment import ObjectModel
from bdd_dsl.models.urirefs import URI_SIM_TYPE_SYS_RES
from bdd_dsl.models.user_story import UserStoryLoader
from bdd_dsl.simulation.common import (
    URL_MM_SIM_SHACL,
    get_path_of_node,
    load_attr_has_config,
    load_attr_path,
)


SPEC_MODEL_URLS = {
    f"{URL_SECORO_M}/acceptance-criteria/bdd/environments/secorolab.env.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/agents/isaac-sim.agn.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/scenes/secorolab-env.scene.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/scenes/isaac-agents.scene.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/templates/pickplace.tmpl.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/pickplace-secorolab-isaac.var.json": "json-ld",
}
EXEC_MODEL_URLS = {
    f"{URL_SECORO_M}/acceptance-criteria/bdd/simulation/secorolab-isaac.sim.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/execution/pickplace-secorolab-isaac.exec.json": "json-ld",
}
SHACL_URLS = {
    URL_MM_SIM_SHACL: "turtle",
    URL_MM_PYTHON_SHACL: "turtle",
}


class BDDExecTest(unittest.TestCase):
    def setUp(self):
        install_resolver()
        self.graph = Dataset()
        for url, fmt in SPEC_MODEL_URLS.items():
            try:
                self.graph.parse(url, format=fmt)
            except HTTPError as e:
                raise RuntimeError(f"HTTPError for URL '{url}': {e}")
        check_shacl_constraints(graph=self.graph, shacl_dict=SHACL_URLS)

        # UserStoryLoader should not need execution info
        self.us_loader = UserStoryLoader(self.graph)

        for url, fmt in EXEC_MODEL_URLS.items():
            try:
                self.graph.parse(url, format=fmt)
            except HTTPError as e:
                raise RuntimeError(f"HTTPError for URL '{url}': {e}")

        check_shacl_constraints(graph=self.graph, shacl_dict=SHACL_URLS)

    def _test_obj_model(self, obj_model: ObjectModel):
        if URI_SIM_TYPE_SYS_RES in obj_model.model_types:
            self.assertTrue(
                len(obj_model.model_type_to_id[URI_SIM_TYPE_SYS_RES]) > 0,
                f"Object '{obj_model.id}' has type '{URI_SIM_TYPE_SYS_RES}' but no corresponding model",
            )
            for model_id in obj_model.model_type_to_id[URI_SIM_TYPE_SYS_RES]:
                # assertion already in function
                _ = get_path_of_node(graph=self.graph, node_id=model_id)

        elif URI_PY_TYPE_MODULE_ATTR in obj_model.model_types:
            self.assertTrue(
                len(obj_model.model_type_to_id[URI_PY_TYPE_MODULE_ATTR]) > 0,
                f"Object '{obj_model.id}' has type '{URI_PY_TYPE_MODULE_ATTR}' but no corresponding model",
            )
            for model_id in obj_model.model_type_to_id[URI_PY_TYPE_MODULE_ATTR]:
                module_name = obj_model.models[model_id].get_attr(key=URI_PY_PRED_MODULE_NAME)
                attr_name = obj_model.models[model_id].get_attr(key=URI_PY_PRED_ATTR_NAME)
                self.assertTrue(
                    module_name is not None,
                    f"PyModuleAttribute model '{model_id}' for Object '{obj_model.id}' has no module name",
                )
                self.assertTrue(
                    attr_name is not None,
                    f"PyModuleAttribute model '{model_id}' for Object '{obj_model.id}' has no attribute name",
                )

    def _test_agn_model(self, agn_model: AgentModel):
        if URI_PY_TYPE_MODULE_ATTR in agn_model.model_types:
            self.assertTrue(
                len(agn_model.model_type_to_id[URI_PY_TYPE_MODULE_ATTR]) > 0,
                f"Agent '{agn_model.id}' has type '{URI_PY_TYPE_MODULE_ATTR}' but no corresponding model",
            )
            for model_id in agn_model.model_type_to_id[URI_PY_TYPE_MODULE_ATTR]:
                module_name = agn_model.models[model_id].get_attr(key=URI_PY_PRED_MODULE_NAME)
                attr_name = agn_model.models[model_id].get_attr(key=URI_PY_PRED_ATTR_NAME)
                self.assertTrue(
                    module_name is not None,
                    f"PyModuleAttribute model '{model_id}' for Agent '{agn_model.id}' has no module name",
                )
                self.assertTrue(
                    attr_name is not None,
                    f"PyModuleAttribute model '{model_id}' for Agent '{agn_model.id}' has no attribute name",
                )

    def test_exec(self):
        for scenario_variant_uris in self.us_loader.get_us_scenario_variants().values():
            for scr_var_uri in scenario_variant_uris:
                scr_var = self.us_loader.load_scenario_variant(
                    full_graph=self.graph, variant_id=scr_var_uri
                )
                scr_var.scene.env_model_loader.register_attr_loaders(
                    load_attr_path, load_attr_has_config, load_py_module_attr
                )
                for obj_id in scr_var.scene.objects:
                    obj_model = scr_var.scene.env_model_loader.load_object_model(
                        obj_id=obj_id, graph=self.graph
                    )
                    self._test_obj_model(obj_model=obj_model)

                for ws_id in scr_var.scene.workspaces:
                    for obj_model in scr_var.scene.env_model_loader.load_ws_objects(
                        ws_id=ws_id, graph=self.graph
                    ):
                        self._test_obj_model(obj_model=obj_model)

                scr_var.scene.agn_model_loader.register_attr_loaders(load_py_module_attr)
                for agn_id in scr_var.scene.agents:
                    agn_model = scr_var.scene.agn_model_loader.load_agent_model(
                        agent_id=agn_id, graph=self.graph
                    )
                    self._test_agn_model(agn_model=agn_model)


if __name__ == "__main__":
    unittest.main()
