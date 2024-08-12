# SPDX-License-Identifier:  GPL-3.0-or-later
from behave.runner import Context
from behave import given, then, when


def before_all_mockup(context: Context):
    g = getattr(context, "model_graph", None)

    assert g is not None, "'model_graph' attribute not found in context"


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


@when('behaviour "{bhv_name}" occurs')
def behaviour_mockup(context: Context, bhv_name: str):
    pass
