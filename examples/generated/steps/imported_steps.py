# SPDX-License-Identifier:  GPL-3.0-or-later
from behave import given, then, when
from bdd_dsl.behave import (
    CLAUSE_BG_AGENTS,
    CLAUSE_BG_OBJECTS,
    CLAUSE_BG_SCENE,
    CLAUSE_BG_WORKSPACES,
    CLAUSE_BHV_PICKPLACE,
    CLAUSE_FL_LOCATED_AT,
    CLAUSE_FL_MOVE_SAFE,
    CLAUSE_FL_SORTED,
    CLAUSE_TC_AFTER_EVT,
    CLAUSE_TC_BEFORE_EVT,
    CLAUSE_TC_DURING,
)
from bdd_dsl.execution.mockup import (
    given_objects_mockup,
    given_scene_mockup,
    given_workspaces_mockup,
    given_agents_mockup,
    is_located_at_mockup,
    move_safe_mockup,
    behaviour_mockup,
)


given(CLAUSE_BG_OBJECTS)(given_objects_mockup)
given(CLAUSE_BG_WORKSPACES)(given_workspaces_mockup)
given(CLAUSE_BG_AGENTS)(given_agents_mockup)
given(CLAUSE_BG_SCENE)(given_scene_mockup)

given(f"{CLAUSE_FL_LOCATED_AT} {CLAUSE_TC_BEFORE_EVT}")(is_located_at_mockup)
given(f"{CLAUSE_FL_LOCATED_AT} {CLAUSE_TC_AFTER_EVT}")(is_located_at_mockup)
then(f"{CLAUSE_FL_LOCATED_AT} {CLAUSE_TC_BEFORE_EVT}")(is_located_at_mockup)
then(f"{CLAUSE_FL_LOCATED_AT} {CLAUSE_TC_AFTER_EVT}")(is_located_at_mockup)
then(f"{CLAUSE_FL_MOVE_SAFE} {CLAUSE_TC_DURING}")(move_safe_mockup)
then(f"{CLAUSE_FL_SORTED} {CLAUSE_TC_AFTER_EVT}")(is_located_at_mockup)

when(CLAUSE_BHV_PICKPLACE)(behaviour_mockup)
