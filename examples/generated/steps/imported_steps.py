from behave import given, then, when
from bdd_dsl.behave import (
    CLAUSE_BG_AGENTS,
    CLAUSE_BG_OBJECTS,
    CLAUSE_BG_WORKSPACES,
    CLAUSE_BHV_PICKPLACE,
    CLAUSE_FL_LOCATED_AT,
    CLAUSE_TC_AFTER_EVT,
    CLAUSE_TC_BEFORE_EVT,
    given_ws_models
)
from bdd_dsl.execution.mockup import (
    given_objects_mockup,
    given_agents_mockup,
    is_located_at_mockup,
    behaviour_mockup
)


given(CLAUSE_BG_OBJECTS)(given_objects_mockup)
given(CLAUSE_BG_WORKSPACES)(given_ws_models)
given(CLAUSE_BG_AGENTS)(given_agents_mockup)

given(f"{CLAUSE_FL_LOCATED_AT} {CLAUSE_TC_BEFORE_EVT}")(is_located_at_mockup)
given(f"{CLAUSE_FL_LOCATED_AT} {CLAUSE_TC_AFTER_EVT}")(is_located_at_mockup)
then(f"{CLAUSE_FL_LOCATED_AT} {CLAUSE_TC_BEFORE_EVT}")(is_located_at_mockup)
then(f"{CLAUSE_FL_LOCATED_AT} {CLAUSE_TC_AFTER_EVT}")(is_located_at_mockup)

when(CLAUSE_BHV_PICKPLACE)(behaviour_mockup)
