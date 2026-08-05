# SPDX-License-Identifier:  GPL-3.0-or-later
from time import sleep
from typing import Any

from behave.model import Scenario
from behave.runner import Context
from rdf_utils.models.common import ModelBase, URIRef
from rdf_utils.models.python import (
    URI_PY_PRED_ATTR_NAME,
    URI_PY_PRED_MODULE_NAME,
    URI_PY_TYPE_MODULE_ATTR,
    load_py_module_attr,
)
from rdf_utils.models.vocab import URI_EXEC_PRED_PATH, URI_EXEC_TYPE_RES_PATH
from rdf_utils.uri import NamespaceManager, try_expand_curie
from rdflib import Graph
from scene_dsl.rdf_parser.scenex import SceneInstanceModel

from bdd_dsl.behave import (
    PARAM_AGN,
    PARAM_EVT,
    PARAM_FROM_EVT,
    PARAM_OBJ,
    PARAM_UNTIL_EVT,
    PARAM_WS,
    load_agn_resources_from_table,
    load_obj_resources_from_table,
    load_str_params,
    load_ws_models_from_table,
    parse_str_param,
)
from bdd_dsl.execution.behaviour import Behaviour
from bdd_dsl.execution.scenario import ScenarioExecutionModel
from bdd_dsl.models.user_story import ScenarioVariantModel, UserStoryLoader


def before_all_mockup(context: Context):
    g = getattr(context, "model_graph", None)
    assert g is not None, "'model_graph' attribute not found in context"

    context.us_loader = UserStoryLoader(graph=g)


def before_scenario(context: Context, scenario: Scenario):
    model_graph = getattr(context, "model_graph", None)
    assert model_graph is not None

    us_loader = getattr(context, "us_loader", None)
    assert us_loader is not None and isinstance(us_loader, UserStoryLoader)

    # scenario outline renders each scenario as
    #   SCHEMA: "{outline_name} -- {examples.name}@{row.id}"
    scr_name_splits = scenario.name.split(" -- ")
    assert len(scr_name_splits) > 0, f"unexpected scenario name: {scenario.name}"
    scr_name = scr_name_splits[0]
    scenario_var_uri = try_expand_curie(
        curie_str=scr_name, ns_manager=model_graph.namespace_manager, quiet=False
    )
    assert scenario_var_uri is not None, f"can't parse '{scr_name}' as URI"

    scenario_var_model = us_loader.load_scenario_variant(
        full_graph=model_graph, variant_id=scenario_var_uri
    )
    assert isinstance(scenario_var_model, ScenarioVariantModel)
    assert len(scenario_var_model.scene.objects) > 0, (
        f"scene '{scenario_var_model.scene.id}' has no object"
    )
    assert len(scenario_var_model.scene.workspaces) > 0, (
        f"scene '{scenario_var_model.scene.id}' has no workspace"
    )
    assert len(scenario_var_model.scene.agents) > 0, (
        f"scene '{scenario_var_model.scene.id}' has no agent"
    )

    scenario_exec = ScenarioExecutionModel(
        graph=model_graph,
        scr_var=scenario_var_model,
        bhv_loaders=[load_py_module_attr],
    )
    context.current_scenario = scenario_var_model
    context.current_scenario_execution = scenario_exec
    context.current_scene_instance = scenario_exec.scene_instance


def _resources_by_type(
    resources: dict[URIRef, ModelBase], model_type: URIRef
) -> tuple[ModelBase, ...]:
    return tuple(resource for resource in resources.values() if model_type in resource.types)


def _check_resource_metadata(
    owner: str, owner_id: URIRef, resources: dict[URIRef, ModelBase]
) -> None:
    for resource in _resources_by_type(resources, URI_PY_TYPE_MODULE_ATTR):
        assert resource.has_attr(key=URI_PY_PRED_MODULE_NAME), (
            f"Python attribute model '{resource.id}' for {owner} '{owner_id}' missing module name"
        )
        assert resource.has_attr(key=URI_PY_PRED_ATTR_NAME), (
            f"Python attribute model '{resource.id}' for {owner} '{owner_id}' missing attribute name"
        )
    for resource in _resources_by_type(resources, URI_EXEC_TYPE_RES_PATH):
        assert resource.has_attr(URI_EXEC_PRED_PATH), (
            f"ResourceWithPath model '{resource.id}' for {owner} '{owner_id}' missing attr path"
        )


def given_objects_mockup(context: Context):
    assert context.table is not None, "no table added to context, expected a list of object URIs"
    assert context.model_graph is not None, "no 'model_graph' in context, expected an rdflib.Graph"
    assert context.current_scenario is not None, (
        "no 'current_scenario' in context, expected a ScenarioVariantModel"
    )
    scene_inst = context.current_scene_instance
    assert isinstance(scene_inst, SceneInstanceModel)
    for obj_id, resources in load_obj_resources_from_table(
        table=context.table, graph=context.model_graph, scene_inst=scene_inst
    ):
        _check_resource_metadata("object", obj_id, resources)


def given_workspaces_mockup(context: Context):
    assert context.table is not None, "no table added to context, expected a list of object URIs"
    assert context.model_graph is not None, "no 'model_graph' in context, expected an rdflib.Graph"
    assert context.current_scenario is not None, (
        "no 'current_scenario' in context, expected a ScenarioVariantModel"
    )
    for ws_model in load_ws_models_from_table(
        table=context.table, graph=context.model_graph, scene=context.current_scenario.scene
    ):
        scene_inst = context.current_scene_instance
        assert isinstance(scene_inst, SceneInstanceModel)
        for obj_id in context.current_scenario.scene.iter_workspace_objects(ws_model.id):
            resources = scene_inst.object_models.get(obj_id, {})
            _check_resource_metadata("object", obj_id, resources)


def given_agents_mockup(context: Context):
    assert context.table is not None, "no table added to context, expected a list of agent URIs"
    assert context.model_graph is not None, "no 'model_graph' in context, expected an rdflib.Graph"
    assert context.current_scenario is not None, (
        "no 'current_scenario' in context, expected an ScenarioVariantModel"
    )
    scene_inst = context.current_scene_instance
    assert isinstance(scene_inst, SceneInstanceModel)
    for agn_id, resources in load_agn_resources_from_table(
        table=context.table, graph=context.model_graph, scene_inst=scene_inst
    ):
        _check_resource_metadata("agent", agn_id, resources)


def given_scene_mockup(context: Context):
    print(f"***setting up scene for scenario: {context.scenario.name}")


def is_located_at_mockup(context: Context, **kwargs: Any):
    params = load_str_params(param_names=[PARAM_OBJ, PARAM_WS, PARAM_EVT], **kwargs)

    assert context.model_graph is not None, "no 'model_graph' in context"
    assert context.current_scenario is not None, (
        "no 'current_scenario' in context, expected an ScenarioVariantModel"
    )

    _, pick_obj_uris = parse_str_param(
        param_str=params[PARAM_OBJ], ns_manager=context.model_graph.namespace_manager
    )
    for obj_uri in pick_obj_uris:
        scene_inst = context.current_scene_instance
        assert isinstance(scene_inst, SceneInstanceModel)
        resources = scene_inst.object_models.get(obj_uri, {})
        _check_resource_metadata("object", obj_uri, resources)

    _, pick_ws_uris = parse_str_param(
        param_str=params[PARAM_WS], ns_manager=context.model_graph.namespace_manager
    )
    for ws_uri in pick_ws_uris:
        if ws_uri not in context.current_scenario.scene.workspaces:
            raise ValueError(
                f"workspace '{ws_uri}' is not in scene '{context.current_scenario.scene.id}'"
            )

    evt_uri = try_expand_curie(
        curie_str=params[PARAM_EVT], ns_manager=context.model_graph.namespace_manager, quiet=False
    )
    assert evt_uri is not None, f"can't parse '{params[PARAM_EVT]}' as URI"


def move_safe_mockup(context: Context, **kwargs: Any):
    assert context.model_graph is not None, "no 'model_graph' in context"
    assert context.current_scenario is not None, (
        "no 'current_scenario' in context, expected an ScenarioVariantModel"
    )

    params = load_str_params(param_names=[PARAM_AGN, PARAM_FROM_EVT, PARAM_UNTIL_EVT], **kwargs)
    parse_str_param(param_str=params[PARAM_AGN], ns_manager=context.model_graph.namespace_manager)


class PickplaceBehaviourMockup(Behaviour):
    agn_ids: list[URIRef] | None
    obj_ids: list[URIRef] | None
    place_ws_ids: list[URIRef] | None

    def __init__(
        self,
        bhv_id: URIRef,
        bhv_types: set[URIRef],
        context: Any,
        ns_manager: NamespaceManager,
        **kwargs,
    ) -> None:
        super().__init__(bhv_id=bhv_id, bhv_types=bhv_types, context=context, **kwargs)

        self.max_count = kwargs.get("max_count", 5)
        self.counter = self.max_count

        self._ns_manager = ns_manager

        self.agn_ids = None
        self.obj_ids = None
        self.place_ws_ids = None

    def is_finished(self, context: Context, **kwargs: Any) -> bool:
        return self.counter <= 0

    def reset(self, context: Context, **kwargs: Any) -> None:
        self.counter = self.max_count

        agn_id_str = kwargs.get("agn_id_str", None)
        assert agn_id_str is not None, "arg 'agn_id_str' not specified'"
        obj_id_str = kwargs.get("obj_id_str", None)
        assert obj_id_str is not None, "arg 'obj_id_str' not specified'"
        ws_id_str = kwargs.get("ws_id_str", None)
        assert ws_id_str is not None, "arg 'ws_id_str not specified'"

        _, agn_uris = parse_str_param(param_str=agn_id_str, ns_manager=self._ns_manager)
        self.agn_ids = []
        for uri in agn_uris:
            assert isinstance(uri, URIRef), f"unexpected agent URI: {uri}"
            self.agn_ids.append(uri)

        _, obj_uris = parse_str_param(param_str=obj_id_str, ns_manager=self._ns_manager)
        self.obj_ids = []
        for uri in obj_uris:
            assert isinstance(uri, URIRef), f"unexpected obj URI: {uri}"
            self.obj_ids.append(uri)

        _, place_ws_uris = parse_str_param(param_str=ws_id_str, ns_manager=self._ns_manager)
        self.place_ws_ids = []
        for uri in place_ws_uris:
            assert isinstance(uri, URIRef), f"unexpected place ws URI: {uri}"
            self.place_ws_ids.append(uri)

    def step(self, context: Context, **kwargs: Any) -> Any:
        assert (
            self.agn_ids is not None and self.obj_ids is not None and self.place_ws_ids is not None
        ), "Behaviour.step: mockup behaviour expects reset() to be called first"

        agn_str = " or ".join(uri.n3(namespace_manager=self._ns_manager) for uri in self.agn_ids)
        obj_str = " or ".join(uri.n3(namespace_manager=self._ns_manager) for uri in self.obj_ids)
        place_ws_str = " or ".join(
            uri.n3(namespace_manager=self._ns_manager) for uri in self.place_ws_ids
        )
        print(f"'{agn_str}' picks '{obj_str}'")
        sleep(0.05)
        print(f"'{agn_str}' places '{obj_str}' at '{place_ws_str}'")
        sleep(0.05)
        self.counter -= 1


def behaviour_mockup(context: Context, **kwargs: Any):
    params = load_str_params(param_names=[PARAM_AGN, PARAM_OBJ, PARAM_WS], **kwargs)

    behaviour_model = getattr(context, "behaviour_model", None)

    if behaviour_model is None:
        scenario_exec = getattr(context, "current_scenario_execution", None)
        assert isinstance(scenario_exec, ScenarioExecutionModel), (
            f"no valid 'current_scenario_execution' added to the context: {scenario_exec}"
        )

        model_graph = getattr(context, "model_graph", None)
        assert isinstance(model_graph, Graph), (
            f"no 'model_graph' of type rdflib.Graph in context: {model_graph}"
        )

        behaviour_model = scenario_exec.load_behaviour_impl(
            context=context,
            ns_manager=model_graph.namespace_manager,
        )
        context.behaviour_model = behaviour_model

    bhv = behaviour_model.behaviour
    assert bhv is not None, f"behaviour not processed for {behaviour_model.id}"
    bhv.reset(
        context=context,
        agn_id_str=params[PARAM_AGN],
        obj_id_str=params[PARAM_OBJ],
        ws_id_str=params[PARAM_WS],
    )
    while not bhv.is_finished(context=context):
        bhv.step(context=context)
