# SPDX-License-Identifier:  GPL-3.0-or-later
from time import sleep
from typing import Any
from behave.runner import Context
from behave.model import Scenario
from behave import given, then, when
from bdd_dsl.execution.common import Behaviour, ExecutionModel
from bdd_dsl.user_story import ScenarioVariantModel, UserStoryLoader


def before_all_mockup(context: Context):
    g = getattr(context, "model_graph", None)
    assert g is not None, "'model_graph' attribute not found in context"

    exec_model = ExecutionModel(graph=g)
    context.execution_model = exec_model
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
    try:
        scenario_var_uri = model_graph.namespace_manager.expand_curie(scr_name)
    except ValueError as e:
        raise RuntimeError(
            f"can't parse behaviour URI '{scr_name}' from scenario '{scenario.name}': {e}"
        )

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


@given("a set of objects")
def given_objects_mockup(context: Context):
    object_set = set()
    assert context.table is not None, "no table added to context, expected a list of objects"
    for row in context.table:
        object_set.add(row["name"])

    context.objects = object_set


@given("a set of workspaces")
def given_workspaces_mockup(context: Context):
    ws_set = set()
    assert context.table is not None, "no table added to context, expected a list of workspaces"
    for row in context.table:
        ws_set.add(row["name"])

    context.workspaces = ws_set


@given("a set of agents")
def given_agents_mockup(context: Context):
    agent_set = set()
    assert context.table is not None, "no table added to context, expected a list of agents"
    for row in context.table:
        agent_set.add(row["name"])

    context.agents = agent_set


@given("specified objects, workspaces and agents are available")
def given_scene_mockup(context: Context):
    assert getattr(context, "objects", None) is not None
    assert getattr(context, "workspaces", None) is not None
    assert getattr(context, "agents", None) is not None


@given('"{pick_obj}" is located at "{pick_ws}"')
@then('"{pick_obj}" is located at "{pick_ws}"')
def is_located_at_mockup_given(context: Context, pick_obj: str, pick_ws: str):
    assert pick_obj in context.objects, f"object '{pick_obj}' unrecognized"
    assert pick_ws in context.workspaces, f"object '{pick_ws}' unrecognized"


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


@when('behaviour "{bhv_name}" occurs')
def behaviour_mockup(context: Context, bhv_name: str):
    behaviour_model = getattr(context, "behaviour_model", None)
    if behaviour_model is None:
        exec_model = getattr(context, "execution_model", None)
        assert exec_model is not None, "no 'execution_model' added to the context"
        assert isinstance(exec_model, ExecutionModel)

        model_graph = getattr(context, "model_graph", None)
        assert model_graph is not None

        try:
            bhv_uri = model_graph.namespace_manager.expand_curie(bhv_name)
        except ValueError as e:
            raise RuntimeError(f"can't parse behaviour URI '{bhv_name}': {e}")

        behaviour_model = exec_model.load_behaviour_impl(context=context, bhv_id=bhv_uri)
        context.behaviour_model = behaviour_model

    bhv = behaviour_model.behaviour
    assert bhv is not None
    bhv.reset(context=context)
    while not bhv.is_finished(context=context):
        bhv.step(context=context)
