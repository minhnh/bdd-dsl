# SPDX-License-Identifier:  GPL-3.0-or-later
from time import sleep
from typing import Any
from behave.runner import Context
from behave.model import Scenario
from behave import given, then, when
from rdf_utils.models.common import ModelLoader
from rdf_utils.models.python import (
    URI_PY_TYPE_MODULE_ATTR,
    URI_PY_PRED_ATTR_NAME,
    URI_PY_PRED_MODULE_NAME,
    load_py_module_attr,
)
from rdf_utils.uri import try_expand_curie
from bdd_dsl.behave import (
    given_ws_models,
    load_obj_models_from_table,
    load_agn_models_from_table,
    parse_str_param,
)
from bdd_dsl.execution.common import Behaviour, ExecutionModel
from bdd_dsl.models.urirefs import URI_SIM_PRED_PATH, URI_SIM_TYPE_RES_PATH
from bdd_dsl.simulation.common import load_attr_has_config, load_attr_path
from bdd_dsl.models.user_story import ScenarioVariantModel, UserStoryLoader


def before_all_mockup(context: Context):
    g = getattr(context, "model_graph", None)
    assert g is not None, "'model_graph' attribute not found in context"

    exec_model = ExecutionModel(graph=g)
    context.execution_model = exec_model
    context.us_loader = UserStoryLoader(graph=g)

    generic_loader = ModelLoader()
    context.ws_model_loader = generic_loader
    context.agn_model_loader = generic_loader


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
    assert (
        len(scenario_var_model.scene.objects) > 0
    ), f"scene '{scenario_var_model.scene.id}' has no object"
    assert (
        len(scenario_var_model.scene.workspaces) > 0
    ), f"scene '{scenario_var_model.scene.id}' has no workspace"
    assert (
        len(scenario_var_model.scene.agents) > 0
    ), f"scene '{scenario_var_model.scene.id}' has no agent"

    scenario_var_model.scene.obj_model_loader.register_attr_loaders(
        load_attr_path, load_attr_has_config, load_py_module_attr
    )
    scenario_var_model.scene.agn_model_loader.register_attr_loaders(load_py_module_attr)
    context.current_scenario = scenario_var_model


@given("a set of objects")
def given_objects_mockup(context: Context):
    assert context.table is not None, "no table added to context, expected a list of object URIs"
    assert context.model_graph is not None, "no 'model_graph' in context, expected an rdflib.Graph"
    assert (
        context.current_scenario is not None
    ), "no 'current_scenario' in context, expected a ScenarioVariantModel"
    for obj_model in load_obj_models_from_table(
        table=context.table, graph=context.model_graph, scene=context.current_scenario.scene
    ):
        if URI_PY_TYPE_MODULE_ATTR in obj_model.model_types:
            for py_model_uri in obj_model.model_type_to_id[URI_PY_TYPE_MODULE_ATTR]:
                py_model = obj_model.models[py_model_uri]
                assert py_model.has_attr(
                    key=URI_PY_PRED_MODULE_NAME
                ), f"Python attribute model '{py_model.id}' for object '{obj_model.id}' missing module name"
                assert py_model.has_attr(
                    key=URI_PY_PRED_ATTR_NAME
                ), f"Python attribute model '{py_model.id}' for object '{obj_model.id}' missing attribute name"

        if URI_SIM_TYPE_RES_PATH in obj_model.model_types:
            for py_model_uri in obj_model.model_type_to_id[URI_SIM_TYPE_RES_PATH]:
                path_model = obj_model.load_first_model_by_type(model_type=URI_SIM_TYPE_RES_PATH)
                assert path_model.has_attr(
                    URI_SIM_PRED_PATH
                ), f"ResourceWithPath model '{path_model.id}' for object '{obj_model.id}' missing attr path"


given("a set of workspaces")(given_ws_models)


@given("a set of agents")
def given_agents_mockup(context: Context):
    assert context.table is not None, "no table added to context, expected a list of agent URIs"
    assert context.model_graph is not None, "no 'model_graph' in context, expected an rdflib.Graph"
    assert (
        context.current_scenario is not None
    ), "no 'current_scenario' in context, expected an ScenarioVariantModel"
    for agn_model in load_agn_models_from_table(
        table=context.table, graph=context.model_graph, scene=context.current_scenario.scene
    ):
        if URI_PY_TYPE_MODULE_ATTR in agn_model.model_types:
            for py_model_uri in agn_model.model_type_to_id[URI_PY_TYPE_MODULE_ATTR]:
                py_model = agn_model.models[py_model_uri]
                assert py_model.has_attr(
                    key=URI_PY_PRED_MODULE_NAME
                ), f"Python attribute model '{py_model.id}' for agent '{agn_model.id}' missing module name"
                assert py_model.has_attr(
                    key=URI_PY_PRED_ATTR_NAME
                ), f"Python attribute model '{py_model.id}' for agent '{agn_model.id}' missing attribute name"


@given("specified objects, workspaces and agents are available")
def given_scene_mockup(context: Context):
    assert getattr(context, "workspaces", None) is not None


@given('"{pick_obj_str}" is located at "{pick_ws_str}" before event "{evt_uri_str}"')
@given('"{pick_obj_str}" is located at "{pick_ws_str}" after event "{evt_uri_str}"')
@then('"{pick_obj_str}" is located at "{pick_ws_str}" before event "{evt_uri_str}"')
@then('"{pick_obj_str}" is located at "{pick_ws_str}" after event "{evt_uri_str}"')
def is_located_at_mockup_given(
    context: Context, pick_obj_str: str, pick_ws_str: str, evt_uri_str: str
):
    assert context.model_graph is not None, "no 'model_graph' in context"
    assert (
        context.current_scenario is not None
    ), "no 'current_scenario' in context, expected an ObjModelLoader"

    _, pick_obj_uris = parse_str_param(
        param_str=pick_obj_str, ns_manager=context.model_graph.namespace_manager
    )
    for obj_uri in pick_obj_uris:
        obj_model = context.current_scenario.scene.load_obj_model(
            graph=context.model_graph, obj_id=obj_uri
        )
        assert obj_model is not None, f"can't load model for object {obj_uri}"
        if URI_PY_TYPE_MODULE_ATTR in obj_model.model_types:
            py_model = obj_model.load_first_model_by_type(URI_PY_TYPE_MODULE_ATTR)
            assert py_model.has_attr(
                key=URI_PY_PRED_MODULE_NAME
            ), f"Python attribute model '{py_model.id}' for object '{obj_model.id}' missing module name"
            assert py_model.has_attr(
                key=URI_PY_PRED_ATTR_NAME
            ), f"Python attribute model '{py_model.id}' for object '{obj_model.id}' missing attribute name"

    _, pick_ws_uris = parse_str_param(
        param_str=pick_ws_str, ns_manager=context.model_graph.namespace_manager
    )
    for ws_uri in pick_ws_uris:
        assert ws_uri in context.workspaces, f"workspace '{ws_uri}' unrecognized"

    evt_uri = try_expand_curie(
        curie_str=evt_uri_str, ns_manager=context.model_graph.namespace_manager, quiet=False
    )
    assert evt_uri is not None, f"can't parse '{evt_uri_str}' as URI"


class PickplaceBehaviourMockup(Behaviour):
    def __init__(self, context: Any, **kwargs) -> None:
        self.max_count = kwargs.get("max_count", 5)
        self.counter = self.max_count

    def is_finished(self, context: Context, **kwargs: Any) -> bool:
        return self.counter <= 0

    def reset(self, context: Context, **kwargs: Any) -> None:
        self.counter = self.max_count

    def step(self, context: Context, **kwargs: Any) -> Any:
        print(self.counter)
        self.counter -= 1
        sleep(0.1)


@when('"{agn_id}" picks "{obj_id}" from "{pick_ws_str}" and places it at "{place_ws}"')
def behaviour_mockup(context: Context, agn_id: str, obj_id: str, pick_ws_str: str, place_ws: str):
    behaviour_model = getattr(context, "behaviour_model", None)
    if behaviour_model is None:
        exec_model = getattr(context, "execution_model", None)
        assert isinstance(
            exec_model, ExecutionModel
        ), f"no valid 'execution_model' added to the context: {exec_model}"

        model_graph = getattr(context, "model_graph", None)
        assert model_graph is not None

        behaviour_model = exec_model.load_behaviour_impl(context=context)
        context.behaviour_model = behaviour_model

    bhv = behaviour_model.behaviour
    assert bhv is not None
    bhv.reset(context=context)
    while not bhv.is_finished(context=context):
        bhv.step(context=context)
