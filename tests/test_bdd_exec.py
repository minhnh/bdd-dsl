# SPDX-License-Identifier:  GPL-3.0-or-later
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from urllib.request import HTTPError

from rdf_utils.constraints import check_shacl_constraints
from rdf_utils.models.python import (
    URI_PY_PRED_ATTR_NAME,
    URI_PY_PRED_MODULE_NAME,
    URI_PY_TYPE_MODULE_ATTR,
)
from rdf_utils.models.vocab import URI_EXEC_PRED_RUNS_SCENE, URI_EXEC_TYPE_SCENE_INST
from rdf_utils.namespace import URL_MM_PYTHON_SHACL, URL_SECORO_M
from rdf_utils.resolver import install_resolver
from rdflib import RDF, Dataset, Graph, Literal, URIRef

from bdd_dsl.execution.common import URL_MM_EXEC_SHACL
from bdd_dsl.execution.scenario import ScenarioExecutionModel
from bdd_dsl.models.observation import ObsPolicyModel, ObservationManager, ObservationStamped
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_HAS_BHV_IMPL,
    URI_BDD_PRED_OF_VARIANT,
    URI_BDD_TYPE_SCENARIO_EXEC,
    URI_BHV_PRED_OF_BHV,
    URI_OBS_PRED_HAS_OBSERVATION,
    URI_OBS_PRED_PROVIDER,
    URI_OBS_TYPE_OBSERVATION,
    URI_OBS_TYPE_POLICY,
    URI_TIME_PRED_AFTER_EVT,
    URI_TIME_PRED_BEFORE_EVT,
    URI_TIME_TYPE_BEFORE_EVT,
)
from bdd_dsl.models.user_story import UserStoryLoader

SPEC_MODEL_URLS = {
    f"{URL_SECORO_M}/acceptance-criteria/bdd/environments/secorolab.env.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/agents/isaac-sim.agn.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/scenes/secorolab-env.scene.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/scenes/isaac-agents.scene.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/templates/pickplace.tmpl.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/variations/pickplace-secorolab-isaac.var.json": "json-ld",
}
EXEC_MODEL_URLS = {
    f"{URL_SECORO_M}/acceptance-criteria/bdd/simulation/secorolab-isaac.sim.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/execution/pickplace-secorolab-isaac.exec.json": "json-ld",
}
SHACL_URLS = {
    URL_MM_EXEC_SHACL: "turtle",
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

    def test_user_story_scenes_load_without_execution_models(self):
        for scenario_variant_uris in self.us_loader.get_us_scenario_variants().values():
            for scr_var_uri in scenario_variant_uris:
                scr_var = self.us_loader.load_scenario_variant(
                    full_graph=self.graph, variant_id=scr_var_uri
                )
                self.assertTrue(scr_var.scene.objects)

    def test_python_observation_policy_evaluates_cached_samples(self):
        graph = Graph()
        policy_uri = URIRef("urn:test:policy")
        observation_uri = URIRef("urn:test:observation")
        provider_uri = URIRef("urn:test:provider")
        graph.add((policy_uri, RDF.type, URI_OBS_TYPE_POLICY))
        graph.add((policy_uri, RDF.type, URI_PY_TYPE_MODULE_ATTR))
        graph.add((policy_uri, URI_PY_PRED_MODULE_NAME, Literal("operator")))
        graph.add((policy_uri, URI_PY_PRED_ATTR_NAME, Literal("truth")))
        graph.add((policy_uri, URI_OBS_PRED_HAS_OBSERVATION, observation_uri))
        graph.add((observation_uri, RDF.type, URI_OBS_TYPE_OBSERVATION))
        graph.add((observation_uri, URI_OBS_PRED_PROVIDER, provider_uri))

        policy = ObsPolicyModel(
            node_id=policy_uri,
            graph=graph,
            fluent_id=URIRef("urn:test:fluent"),
            fluent_types=set(),
            duration_type=URI_TIME_TYPE_BEFORE_EVT,
            start_event=None,
            end_event=URIRef("urn:test:end"),
            horizon=10.0,
        )
        manager = ObservationManager(scr_exec=SimpleNamespace())
        manager.obs_policies[policy_uri] = policy
        manager._observation_policy_registry[observation_uri] = policy_uri

        accepted, _ = manager.update_observation(
            ObservationStamped(observation_uri, provider_uri, 2.0, object())
        )
        self.assertTrue(accepted)
        self.assertEqual(policy.trinary_timeline[0].stamp, 2.0)
        self.assertTrue(policy.trinary_timeline[0].trinary)

        accepted, detail = manager.update_observation(
            ObservationStamped(observation_uri, provider_uri, 1.0, object())
        )
        self.assertFalse(accepted)
        self.assertIn("older", detail)
        self.assertEqual(manager.observation_cache[observation_uri].stamp, 2.0)
        self.assertEqual(len(policy.trinary_timeline), 1)

        with self.assertRaisesRegex(ValueError, "expected"):
            manager.update_observation(
                ObservationStamped(observation_uri, URIRef("urn:test:wrong-provider"), 3.0, object())
            )

    def test_scenario_execution_selects_exact_scene_instance(self):
        graph = Graph()
        variant = URIRef("urn:test:variant")
        execution = URIRef("urn:test:execution")
        scene_inst = URIRef("urn:test:scene-instance")
        bhv_impl = URIRef("urn:test:behaviour-implementation")
        behaviour = URIRef("urn:test:behaviour")
        graph.add((execution, RDF.type, URI_BDD_TYPE_SCENARIO_EXEC))
        graph.add((execution, URI_BDD_PRED_OF_VARIANT, variant))
        graph.add((execution, URI_EXEC_PRED_RUNS_SCENE, scene_inst))
        graph.add((scene_inst, RDF.type, URI_EXEC_TYPE_SCENE_INST))
        graph.add((execution, URI_BDD_PRED_HAS_BHV_IMPL, bhv_impl))
        graph.add((bhv_impl, RDF.type, URIRef("urn:test:Implementation")))
        graph.add((bhv_impl, URI_BHV_PRED_OF_BHV, behaviour))
        graph.add((behaviour, RDF.type, URIRef("urn:test:Behaviour")))
        scr_var = SimpleNamespace(id=variant, tmpl=object())
        duration = {
            URI_TIME_PRED_AFTER_EVT: URIRef("urn:test:start"),
            URI_TIME_PRED_BEFORE_EVT: URIRef("urn:test:end"),
        }

        with patch("bdd_dsl.execution.scenario.get_duration", return_value=duration):
            model = ScenarioExecutionModel(graph, scr_var, bhv_loaders=[])
            self.assertEqual(model.scene_inst_id, scene_inst)

            other_scene = URIRef("urn:test:other-scene-instance")
            graph.add((other_scene, RDF.type, URI_EXEC_TYPE_SCENE_INST))
            graph.add((execution, URI_EXEC_PRED_RUNS_SCENE, other_scene))
            with self.assertRaisesRegex(ValueError, "exactly 1 scene instance"):
                ScenarioExecutionModel(graph, scr_var, bhv_loaders=[])
            graph.remove((execution, URI_EXEC_PRED_RUNS_SCENE, other_scene))

            graph.remove((execution, URI_EXEC_PRED_RUNS_SCENE, scene_inst))
            with self.assertRaisesRegex(ValueError, "exactly 1 scene instance"):
                ScenarioExecutionModel(graph, scr_var, bhv_loaders=[])

            graph.add((execution, URI_EXEC_PRED_RUNS_SCENE, URIRef("urn:test:not-scene")))
            with self.assertRaisesRegex(TypeError, "non-SceneInstance"):
                ScenarioExecutionModel(graph, scr_var, bhv_loaders=[])


if __name__ == "__main__":
    unittest.main()
