# SPDX-License-Identifier:  GPL-3.0-or-later
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from urllib.request import HTTPError

from rdf_utils.constraints import check_shacl_constraints
from rdf_utils.models.common import ModelBase
from rdf_utils.models.python import (
    URI_PY_PRED_ATTR_NAME,
    URI_PY_PRED_MODULE_NAME,
    URI_PY_TYPE_MODULE_ATTR,
)
from rdf_utils.models.vocab import URI_EXEC_PRED_RUNS_SCENE, URI_EXEC_TYPE_SCENE_INST
from rdf_utils.namespace import URL_MM_PYTHON_SHACL, URL_SECORO_M
from rdf_utils.resolver import install_resolver
from rdflib import RDF, Dataset, Graph, Literal, URIRef
from trinary import Unknown

from bdd_dsl.execution.common import URL_MM_EXEC_SHACL
from bdd_dsl.execution.scenario import ScenarioExecutionModel
from bdd_dsl.models.observation import (
    EntityObservation,
    ObservationManager,
    ObservationPolicyEvaluator,
    ObservationStamped,
    ObsPolicyModel,
    TrinaryStamped,
    trin_policy_and,
)
from bdd_dsl.models.time_constraint import process_time_constraint_model
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_HAS_BHV_IMPL,
    URI_BDD_PRED_OF_CLAUSE,
    URI_BDD_PRED_OF_SCENE,
    URI_BDD_PRED_OF_VARIANT,
    URI_BDD_TYPE_SCENARIO_EXEC,
    URI_BHV_PRED_OF_BHV,
    URI_BHV_TYPE_BHV,
    URI_OBS_PRED_ENTITY_MAPPER,
    URI_OBS_PRED_HAS_EVALUATOR,
    URI_OBS_PRED_HAS_OBSERVATION,
    URI_OBS_PRED_OBSERVES_TARGET,
    URI_OBS_PRED_POLICY,
    URI_OBS_PRED_PROVIDER,
    URI_OBS_PRED_TIME_EXTRACTOR,
    URI_OBS_TYPE_EVALUATED_POLICY,
    URI_OBS_TYPE_OBSERVATION,
    URI_OBS_TYPE_POLICY,
    URI_TIME_PRED_AFTER_EVT,
    URI_TIME_PRED_BEFORE_EVT,
    URI_TIME_PRED_HRZN_SEC,
    URI_TIME_TYPE_BEFORE_EVT,
    URI_TIME_TYPE_DURING,
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


def test_trinary_policy_and_reports_final_result():
    value, reason = trin_policy_and(
        [
            TrinaryStamped(1.0, False, "object is not at pick workspace"),
            TrinaryStamped(2.0, False, "object collides with place workspace"),
            TrinaryStamped(3.0, True, "ignored success"),
        ]
    )

    assert value is False
    assert reason == "at least one assertion is false"


def test_default_observation_evaluator_handles_empty_and_non_empty_samples():
    class Evaluator(ObservationPolicyEvaluator):
        def _evaluate_samples(self, observations):
            return False, f"{len(observations)} samples"

    evaluator = Evaluator((True, "no collision recorded"))
    assert evaluator.evaluate([]) == (True, "no collision recorded")
    assert evaluator.evaluate(
        [ObservationStamped(URIRef("urn:test:obs"), URIRef("urn:test:provider"), 1.0, True)]
    ) == (False, "1 samples")


def test_policy_result_uses_default_until_an_accepted_sample_exists():
    policy_uri = URIRef("urn:test:policy-default")
    observation_uri = URIRef("urn:test:obs")
    provider_uri = URIRef("urn:test:provider")
    graph = Graph()
    graph.add((policy_uri, RDF.type, URI_OBS_TYPE_POLICY))
    graph.add((policy_uri, URI_OBS_PRED_HAS_OBSERVATION, observation_uri))
    graph.add((observation_uri, RDF.type, URI_OBS_TYPE_OBSERVATION))
    graph.add((observation_uri, URI_OBS_PRED_PROVIDER, provider_uri))
    add_python_role(graph, policy_uri, URI_OBS_PRED_HAS_EVALUATOR, "evaluator")
    add_before_policy_time(graph, policy_uri, URIRef("urn:test:end-default"))
    policy = ObsPolicyModel(
        node_id=policy_uri,
        graph=graph,
        fluent_id=URIRef("urn:test:fluent-default"),
        fluent_types={URI_TIME_TYPE_BEFORE_EVT},
    )

    class Evaluator(ObservationPolicyEvaluator):
        def _evaluate_samples(self, observations):
            return observations[0].value, "observation value"

    policy.evaluator = Evaluator((True, "no collision recorded"))
    assert policy.get_result(1.0, trin_policy_and).trinary is True

    accepted, _ = policy.add_samples(
        [ObservationStamped(observation_uri, provider_uri, 2.0, False)]
    )
    assert accepted
    result = policy.get_result(2.0, trin_policy_and)
    assert result.trinary is False
    assert result.reason == "at least one assertion is false"

    result = policy.get_result(12.0, trin_policy_and)
    assert result.trinary is True
    assert result.reason == "no collision recorded"


def test_before_policy_closes_on_the_final_event_relative_window():
    policy_uri = URIRef("urn:test:policy-close")
    observation_uri = URIRef("urn:test:obs-close")
    provider_uri = URIRef("urn:test:provider-close")
    end_uri = URIRef("urn:test:end-close")
    graph = Graph()
    graph.add((policy_uri, RDF.type, URI_OBS_TYPE_POLICY))
    graph.add((policy_uri, URI_OBS_PRED_HAS_OBSERVATION, observation_uri))
    graph.add((observation_uri, RDF.type, URI_OBS_TYPE_OBSERVATION))
    graph.add((observation_uri, URI_OBS_PRED_PROVIDER, provider_uri))
    add_python_role(graph, policy_uri, URI_OBS_PRED_HAS_EVALUATOR, "evaluator")
    add_before_policy_time(graph, policy_uri, end_uri)
    policy = ObsPolicyModel(
        node_id=policy_uri,
        graph=graph,
        fluent_id=URIRef("urn:test:fluent-close"),
        fluent_types={URI_TIME_TYPE_BEFORE_EVT},
    )

    class Evaluator(ObservationPolicyEvaluator):
        def _evaluate_samples(self, observations):
            return observations[0].value, "observation value"

    policy.evaluator = Evaluator()
    assert policy.add_samples([ObservationStamped(observation_uri, provider_uri, 9.0, False)])[0]
    assert policy.add_samples([ObservationStamped(observation_uri, provider_uri, 14.0, True)])[0]
    assert policy.get_result(14.0, trin_policy_and).trinary is False

    policy.on_event(end_uri, 20.0)

    result = policy.get_result(100.0, trin_policy_and)
    assert result.trinary is True


EXEC_MODEL_URLS = {
    f"{URL_SECORO_M}/acceptance-criteria/bdd/simulation/secorolab-isaac.sim.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/execution/pickplace-secorolab-isaac.exec.json": "json-ld",
}
SHACL_URLS = {
    URL_MM_EXEC_SHACL: "turtle",
    URL_MM_PYTHON_SHACL: "turtle",
}


def _create_scenario_exec_graph(
    execution_id: URIRef | None = None,
    variant_id: URIRef | None = None,
    tmpl_id: URIRef | None = None,
    scene_id: URIRef | None = None,
    scene_inst_id: URIRef | None = None,
    bhv_id: URIRef | None = None,
    bhv_impl_id: URIRef | None = None,
) -> Graph:
    if execution_id is None:
        execution_id = URIRef("urn:test:execution")
    if variant_id is None:
        variant_id = URIRef("urn:test:variant")
    if tmpl_id is None:
        tmpl_id = URIRef("urn:test:template")
    if scene_id is None:
        scene_id = URIRef("urn:test:scene")
    if scene_inst_id is None:
        scene_inst_id = URIRef("urn:test:scene-instance")
    if bhv_id is None:
        bhv_id = URIRef("urn:test:behaviour")
    if bhv_impl_id is None:
        bhv_impl_id = URIRef("urn:test:behaviour-implementation")

    graph = Graph()
    graph.add((execution_id, RDF.type, URI_BDD_TYPE_SCENARIO_EXEC))
    graph.add((execution_id, URI_BDD_PRED_OF_VARIANT, variant_id))
    graph.add((execution_id, URI_EXEC_PRED_RUNS_SCENE, scene_inst_id))
    graph.add((scene_inst_id, RDF.type, URI_EXEC_TYPE_SCENE_INST))
    graph.add((scene_inst_id, URI_BDD_PRED_OF_SCENE, scene_id))
    graph.add((execution_id, URI_BDD_PRED_HAS_BHV_IMPL, bhv_impl_id))
    graph.add((bhv_impl_id, RDF.type, URIRef("urn:test:Implementation")))
    graph.add((bhv_impl_id, URI_BHV_PRED_OF_BHV, bhv_id))
    graph.add((bhv_id, RDF.type, URI_BHV_TYPE_BHV))
    graph.add((tmpl_id, RDF.type, URI_TIME_TYPE_DURING))
    graph.add((tmpl_id, URI_TIME_PRED_AFTER_EVT, URIRef("urn:test:start")))
    graph.add((tmpl_id, URI_TIME_PRED_BEFORE_EVT, URIRef("urn:test:end")))
    graph.add((tmpl_id, RDF.type, URI_TIME_TYPE_DURING))
    graph.add((tmpl_id, URI_TIME_PRED_AFTER_EVT, URIRef("urn:test:start")))
    graph.add((tmpl_id, URI_TIME_PRED_BEFORE_EVT, URIRef("urn:test:end")))
    return graph


def add_before_policy_time(graph, policy_uri, end_uri):
    graph.add((policy_uri, RDF.type, URI_TIME_TYPE_BEFORE_EVT))
    graph.add((policy_uri, URI_TIME_PRED_BEFORE_EVT, end_uri))
    graph.add((policy_uri, URI_TIME_PRED_HRZN_SEC, Literal(10.0)))


class FixtureEvaluator(ObservationPolicyEvaluator):
    def _evaluate_samples(self, observations):
        return bool(observations), "fixture"


def fixture_timestamp(_, receipt_stamp):
    return receipt_stamp + 1


def fixture_entity_mapper(observation, _, targets):
    return [EntityObservation(targets[0], observation)]


def add_python_role(graph, policy_uri, predicate, name, attr_name="FixtureEvaluator"):
    role_uri = URIRef(f"{policy_uri}/{name}")
    if predicate == URI_OBS_PRED_HAS_EVALUATOR:
        graph.add((policy_uri, RDF.type, URI_OBS_TYPE_EVALUATED_POLICY))
        add_python_role(
            graph,
            policy_uri,
            URI_OBS_PRED_TIME_EXTRACTOR,
            "time-extractor",
            "fixture_timestamp",
        )
    graph.add((policy_uri, predicate, role_uri))
    graph.add((role_uri, RDF.type, URI_PY_TYPE_MODULE_ATTR))
    graph.add((role_uri, URI_PY_PRED_MODULE_NAME, Literal("test_bdd_exec")))
    graph.add((role_uri, URI_PY_PRED_ATTR_NAME, Literal(attr_name)))
    return role_uri


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
        target_uri = URIRef("urn:test:target-variable")
        bound_target_uri = URIRef("urn:test:target")
        graph.add((policy_uri, RDF.type, URI_OBS_TYPE_POLICY))
        graph.add((policy_uri, URI_OBS_PRED_HAS_OBSERVATION, observation_uri))
        graph.add((observation_uri, RDF.type, URI_OBS_TYPE_OBSERVATION))
        graph.add((observation_uri, URI_OBS_PRED_PROVIDER, provider_uri))
        graph.add((observation_uri, URI_OBS_PRED_OBSERVES_TARGET, target_uri))
        graph.add((provider_uri, RDF.type, URIRef("urn:test:provider-type")))
        add_python_role(graph, policy_uri, URI_OBS_PRED_HAS_EVALUATOR, "evaluator")
        add_python_role(
            graph,
            policy_uri,
            URI_OBS_PRED_ENTITY_MAPPER,
            "entity-mapper",
            "fixture_entity_mapper",
        )
        fluent_id = URIRef("urn:test:fluent")
        graph.add((policy_uri, URI_BDD_PRED_OF_CLAUSE, fluent_id))
        add_before_policy_time(graph, policy_uri, URIRef("urn:test:end"))

        policy = ObsPolicyModel(
            node_id=policy_uri,
            graph=graph,
            fluent_id=fluent_id,
            fluent_types={URI_TIME_TYPE_BEFORE_EVT},
        )

        class TruthEvaluator(ObservationPolicyEvaluator):
            def _evaluate_samples(self, observations: list[ObservationStamped]) -> tuple[bool, str]:
                return bool(observations), "sample exists"

        self.assertEqual(policy.observation_targets[observation_uri], target_uri)
        manager = ObservationManager(
            scr_exec=SimpleNamespace(
                obs_policy_fluents={policy_uri: policy.fluent_id}, scene_instance=None
            )
        )
        manager.register_fluent_obs(
            graph,
            SimpleNamespace(id=policy.fluent_id, types={URI_TIME_TYPE_BEFORE_EVT}),
            obs_loaders=[],
        )
        self.assertEqual(manager.providers[provider_uri].id, provider_uri)
        policy = manager.obs_policies[policy_uri]
        policy.evaluator = TruthEvaluator()

        manager.bind_observation_targets({target_uri: bound_target_uri})
        self.assertEqual(policy.observation_targets[observation_uri], bound_target_uri)
        self.assertEqual(
            manager.observation_targets_for_provider(provider_uri),
            {observation_uri: bound_target_uri},
        )
        self.assertEqual(manager.update_provider_observation(provider_uri, object(), 1.0), {})
        self.assertNotIn(observation_uri, manager.observation_cache)

        manager.load_provider_adapters(graph)
        results = manager.update_provider_observation(provider_uri, object(), 1.0)
        self.assertEqual(results, {policy_uri: (True, "")})
        self.assertEqual(policy.trinary_timeline[0].stamp, 2.0)
        self.assertTrue(policy.trinary_timeline[0].trinary)

        accepted, detail = manager.update_observations(
            [ObservationStamped(observation_uri, provider_uri, 1.0, object())]
        )[policy_uri]
        self.assertFalse(accepted)
        self.assertIn("older", detail)
        self.assertEqual(manager.observation_cache[observation_uri].stamp, 2.0)
        self.assertEqual(len(policy.trinary_timeline), 1)

        with self.assertRaisesRegex(ValueError, "expected"):
            manager.update_observations(
                [
                    ObservationStamped(
                        observation_uri, URIRef("urn:test:wrong-provider"), 3.0, object()
                    )
                ]
            )

    def test_shared_provider_rejects_conflicting_adapters(self):
        provider_uri = URIRef("urn:test:provider")
        manager = ObservationManager(scr_exec=SimpleNamespace())
        manager.providers[provider_uri] = SimpleNamespace()
        manager.obs_policies = {
            URIRef("urn:test:first-policy"): SimpleNamespace(
                observation_providers={URIRef("urn:test:first-observation"): provider_uri},
                time_extractor_id=URIRef("urn:test:first-extractor"),
                entity_mapper_id=None,
            ),
            URIRef("urn:test:second-policy"): SimpleNamespace(
                observation_providers={URIRef("urn:test:second-observation"): provider_uri},
                time_extractor_id=URIRef("urn:test:second-extractor"),
                entity_mapper_id=None,
            ),
        }

        with self.assertRaisesRegex(ValueError, "conflicting adapters"):
            manager.load_provider_adapters(Graph())

    def test_observation_batch_evaluates_policy_once_after_caching_all_samples(self):
        graph = Graph()
        policy_uri = URIRef("urn:test:policy")
        provider_uri = URIRef("urn:test:provider")
        observation_uris = [URIRef(f"urn:test:observation-{i}") for i in range(2)]
        graph.add((policy_uri, RDF.type, URI_OBS_TYPE_POLICY))
        for observation_uri in observation_uris:
            graph.add((policy_uri, URI_OBS_PRED_HAS_OBSERVATION, observation_uri))
            graph.add((observation_uri, RDF.type, URI_OBS_TYPE_OBSERVATION))
            graph.add((observation_uri, URI_OBS_PRED_PROVIDER, provider_uri))
        add_python_role(graph, policy_uri, URI_OBS_PRED_HAS_EVALUATOR, "evaluator")
        add_before_policy_time(graph, policy_uri, URIRef("urn:test:end"))

        policy = ObsPolicyModel(
            node_id=policy_uri,
            graph=graph,
            fluent_id=URIRef("urn:test:fluent"),
            fluent_types={URI_TIME_TYPE_BEFORE_EVT},
        )
        calls = []

        class BatchEvaluator(ObservationPolicyEvaluator):
            def _evaluate_samples(self, observations):
                calls.append(observations)
                return True, "batch complete"

        policy.evaluator = BatchEvaluator()
        manager = ObservationManager(scr_exec=SimpleNamespace())
        manager.obs_policies[policy_uri] = policy
        manager._observation_policy_registry.update(
            {observation_uri: policy_uri for observation_uri in observation_uris}
        )
        manager.bind_observation_targets({None: URIRef("urn:test:must-not-bind")})
        self.assertTrue(all(policy.observation_targets[uri] is None for uri in observation_uris))

        results = manager.update_observations(
            [ObservationStamped(observation_uris[0], provider_uri, 1.0, True)]
        )
        self.assertTrue(results[policy_uri][0])
        self.assertEqual(calls, [])
        self.assertIs(policy.get_result(1.0, trin_policy_and).trinary, Unknown)

        results = manager.update_observations(
            [
                ObservationStamped(observation_uri, provider_uri, stamp, True)
                for observation_uri, stamp in zip(observation_uris, (1.0, 2.0), strict=True)
            ]
        )

        self.assertEqual(results, {policy_uri: (True, "")})
        self.assertEqual(len(calls), 1)
        self.assertEqual(policy.trinary_timeline[-1].stamp, 2.0)

        cached_snapshot = dict(manager.observation_cache)
        results = manager.update_observations(
            [
                ObservationStamped(observation_uris[0], provider_uri, 0.0, False),
                ObservationStamped(observation_uris[1], provider_uri, 3.0, False),
            ]
        )

        self.assertEqual(
            results,
            {policy_uri: (False, "(observation) older than cached sample")},
        )
        self.assertEqual(manager.observation_cache, cached_snapshot)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(policy.trinary_timeline), 1)

        results = manager.update_observations(
            [ObservationStamped(observation_uris[0], provider_uri, 13.0, False)]
        )

        self.assertTrue(results[policy_uri][0])
        self.assertEqual(len(calls), 1)
        self.assertIs(policy.get_result(13.0, trin_policy_and).trinary, Unknown)

        results = manager.update_observations(
            [ObservationStamped(observation_uris[1], provider_uri, 14.0, True)]
        )

        self.assertTrue(results[policy_uri][0])
        self.assertEqual(len(calls), 2)
        self.assertIs(policy.get_result(14.0, trin_policy_and).trinary, True)

    def test_python_observation_policy_instantiates_callable_class_once(self):
        class StatefulEvaluator(ObservationPolicyEvaluator):
            def __init__(self):
                super().__init__()
                self.calls = 0

            def _evaluate_samples(self, observations):
                self.calls += 1
                return bool(observations), "stateful sample exists"

        graph = Graph()
        policy_uri = URIRef("urn:test:policy")
        observation_uri = URIRef("urn:test:observation")
        provider_uri = URIRef("urn:test:provider")
        graph.add((policy_uri, RDF.type, URI_OBS_TYPE_POLICY))
        add_python_role(graph, policy_uri, URI_OBS_PRED_HAS_EVALUATOR, "evaluator")
        graph.add((policy_uri, URI_OBS_PRED_HAS_OBSERVATION, observation_uri))
        graph.add((observation_uri, RDF.type, URI_OBS_TYPE_OBSERVATION))
        graph.add((observation_uri, URI_OBS_PRED_PROVIDER, provider_uri))
        add_before_policy_time(graph, policy_uri, URIRef("urn:test:end"))

        with patch(
            "bdd_dsl.models.observation.import_attr_from_model", return_value=StatefulEvaluator
        ):
            policy = ObsPolicyModel(
                node_id=policy_uri,
                graph=graph,
                fluent_id=URIRef("urn:test:fluent"),
                fluent_types={URI_TIME_TYPE_BEFORE_EVT},
            )

        self.assertIsInstance(policy.evaluator, StatefulEvaluator)
        sample = ObservationStamped(observation_uri, provider_uri, 1.0, True)
        self.assertTrue(policy.evaluator.evaluate([sample])[0])
        self.assertTrue(policy.evaluator.evaluate([sample])[0])
        self.assertEqual(policy.evaluator.calls, 2)

    def test_scenario_execution_rejects_multiple_policies_for_one_fluent(self):
        execution_id = URIRef("urn:test:execution")
        tmpl_id = URIRef("urn:test:template")
        variant_id = URIRef("urn:test:variant")
        scene_id = URIRef("urn:test:scene")
        scene_inst_id = URIRef("urn:test:scene-instance")
        graph = _create_scenario_exec_graph(
            execution_id=execution_id,
            variant_id=variant_id,
            tmpl_id=tmpl_id,
            scene_id=scene_id,
            scene_inst_id=scene_inst_id,
        )
        tmpl = ModelBase(node_id=tmpl_id, graph=graph)
        process_time_constraint_model(constraint=tmpl, graph=graph)
        scr_var = SimpleNamespace(id=variant_id, tmpl=tmpl, scene=SimpleNamespace(id=scene_id))
        fluent = URIRef("urn:test:fluent-duplicate-policy")
        policy_a = URIRef("urn:test:policy-a")
        policy_b = URIRef("urn:test:policy-b")
        for policy in (policy_a, policy_b):
            graph.add((execution_id, URI_OBS_PRED_POLICY, policy))
            graph.add((policy, RDF.type, URI_OBS_TYPE_POLICY))
            graph.add((policy, URI_BDD_PRED_OF_CLAUSE, fluent))

        with self.assertRaisesRegex(ValueError, "multiple policies"):
            ScenarioExecutionModel(graph, scr_var, bhv_loaders=[])

    def test_scenario_execution_selects_exact_scene_instance(self):
        execution = URIRef("urn:test:execution")
        variant = URIRef("urn:test:variant")
        scene_inst = URIRef("urn:test:scene-instance")
        scene = URIRef("urn:test:scene")
        tmpl_id = URIRef("urn:test:template")
        graph = _create_scenario_exec_graph(
            execution_id=execution,
            tmpl_id=tmpl_id,
            variant_id=variant,
            scene_id=scene,
            scene_inst_id=scene_inst,
        )
        tmpl = ModelBase(node_id=tmpl_id, graph=graph)
        process_time_constraint_model(constraint=tmpl, graph=graph)
        scr_var = SimpleNamespace(id=variant, tmpl=tmpl, scene=SimpleNamespace(id=scene))

        model = ScenarioExecutionModel(graph, scr_var, bhv_loaders=[])
        self.assertEqual(model.scene_instance.id, scene_inst)

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
