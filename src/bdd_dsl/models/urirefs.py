# SPDX-License-Identifier:  GPL-3.0-or-later
from rdf_utils.namespace import (
    NS_MM_ENV,
    NS_MM_AGN,
    NS_MM_TIME,
)
from bdd_dsl.models.namespace import (
    NS_MM_BDD,
    NS_MM_BHV,
    NS_MM_SIM,
    NS_MM_TASK,
)

# Environment
URI_ENV_TYPE_OBJ = NS_MM_ENV["Object"]
URI_ENV_TYPE_WS = NS_MM_ENV["Workspace"]
URI_ENV_TYPE_WS_WS = NS_MM_ENV["WorkspaceHasWorkspace"]
URI_ENV_TYPE_WS_OBJ = NS_MM_ENV["WorkspaceHasObject"]
URI_ENV_TYPE_RIGID_OBJ = NS_MM_ENV["RigidObject"]
URI_ENV_TYPE_MOD_OBJ = NS_MM_ENV["ModelledObject"]
URI_ENV_TYPE_OBJ_MODEL = NS_MM_ENV["ObjectModel"]
URI_ENV_PRED_HAS_OBJ_MODEL = NS_MM_ENV["has-object-model"]
URI_ENV_PRED_HAS_OBJ = NS_MM_ENV["has-object"]
URI_ENV_PRED_OF_OBJ = NS_MM_ENV["of-object"]
URI_ENV_PRED_HAS_WS = NS_MM_ENV["has-workspace"]
URI_ENV_PRED_OF_WS = NS_MM_ENV["of-workspace"]

# Agent
URI_AGN_TYPE_AGN = NS_MM_AGN["Agent"]
URI_AGN_TYPE_MOD_AGN = NS_MM_AGN["ModelledAgent"]
URI_AGN_TYPE_AGN_MODEL = NS_MM_AGN["AgentModel"]
URI_AGN_PRED_OF_AGN = NS_MM_AGN["of-agent"]
URI_AGN_PRED_HAS_AGN = NS_MM_AGN["has-agent"]
URI_AGN_PRED_HAS_AGN_MODEL = NS_MM_AGN["has-agent-model"]

# Behaviour
URI_BHV_TYPE_BHV = NS_MM_BHV["Behaviour"]
URI_BHV_PRED_OF_BHV = NS_MM_BHV["of-behaviour"]
URI_BHV_TYPE_PICK = NS_MM_BHV["Pick"]
URI_BHV_TYPE_PLACE = NS_MM_BHV["Place"]
URI_BHV_PRED_TARGET_OBJ = NS_MM_BHV["target-object"]
URI_BHV_PRED_TARGET_WS = NS_MM_BHV["target-workspace"]
URI_BHV_PRED_TARGET_AGN = NS_MM_BHV["target-agent"]

# Time
URI_TIME_TYPE_TC = NS_MM_TIME["TimeConstraint"]
URI_TIME_TYPE_BEFORE_EVT = NS_MM_TIME["BeforeEventConstraint"]
URI_TIME_TYPE_AFTER_EVT = NS_MM_TIME["AfterEventConstraint"]
URI_TIME_TYPE_DURING = NS_MM_TIME["DuringEventsConstraint"]
URI_TIME_PRED_BEFORE_EVT = NS_MM_TIME["before-event"]
URI_TIME_PRED_AFTER_EVT = NS_MM_TIME["after-event"]

# Task
URI_TASK_TYPE_TASK = NS_MM_TASK["Task"]
URI_TASK_PRED_OF_TASK = NS_MM_TASK["of-task"]

# Simulation
URI_SIM_TYPE_SYS_RES = NS_MM_SIM["SystemResource"]
URI_SIM_TYPE_RES_PATH = NS_MM_SIM["ResourceWithPath"]
URI_SIM_PRED_HAS_CONFIG = NS_MM_SIM["has-config"]
URI_SIM_PRED_PATH = NS_MM_SIM["path"]

# BDD
URI_BDD_TYPE_US = NS_MM_BDD["UserStory"]
URI_BDD_TYPE_SCENARIO = NS_MM_BDD["Scenario"]
URI_BDD_TYPE_GIVEN = NS_MM_BDD["Given"]
URI_BDD_TYPE_WHEN = NS_MM_BDD["When"]
URI_BDD_TYPE_THEN = NS_MM_BDD["Then"]
URI_BDD_TYPE_SCENARIO_TMPL = NS_MM_BDD["ScenarioTemplate"]
URI_BDD_TYPE_SCENARIO_VARIANT = NS_MM_BDD["ScenarioVariant"]
URI_BDD_TYPE_VARIABLE = NS_MM_BDD["ScenarioVariable"]
URI_BDD_TYPE_TASK_VAR = NS_MM_BDD["TaskVariation"]
URI_BDD_TYPE_TABLE_VAR = NS_MM_BDD["TableVariation"]
URI_BDD_TYPE_CART_PRODUCT = NS_MM_BDD["CartesianProductVariation"]
URI_BDD_TYPE_FORALL = NS_MM_BDD["ForAll"]
URI_BDD_TYPE_EXISTS = NS_MM_BDD["ThereExists"]
URI_BDD_TYPE_SCENE = NS_MM_BDD["Scene"]
URI_BDD_TYPE_SCENE_OBJ = NS_MM_BDD["SceneHasObjects"]
URI_BDD_TYPE_SCENE_WS = NS_MM_BDD["SceneHasWorkspaces"]
URI_BDD_TYPE_SCENE_AGN = NS_MM_BDD["SceneHasAgents"]
URI_BDD_TYPE_SET = NS_MM_BDD["Set"]
URI_BDD_TYPE_CONST_SET = NS_MM_BDD["ConstantSet"]
URI_BDD_TYPE_WHEN_BHV = NS_MM_BDD["WhenBehaviour"]
URI_BDD_TYPE_FLUENT_CLAUSE = NS_MM_BDD["FluentClause"]
URI_BDD_TYPE_LOCATED_AT = NS_MM_BDD["LocatedAtPredicate"]
URI_BDD_TYPE_IS_HELD = NS_MM_BDD["IsHeldPredicate"]
URI_BDD_TYPE_MOVE_SAFE = NS_MM_BDD["MoveSafelyPredicate"]
URI_BDD_TYPE_SORTED = NS_MM_BDD["SortedIntoPredicate"]
URI_BDD_TYPE_SCENARIO_EXEC = NS_MM_BDD["ScenarioExecution"]
URI_BDD_TYPE_BHV_IMPL = NS_MM_BDD["BehaviourImplementation"]
URI_BDD_PRED_GIVEN = NS_MM_BDD["given"]
URI_BDD_PRED_WHEN = NS_MM_BDD["when"]
URI_BDD_PRED_THEN = NS_MM_BDD["then"]
URI_BDD_PRED_OF_SCENARIO = NS_MM_BDD["of-scenario"]
URI_BDD_PRED_OF_TMPL = NS_MM_BDD["of-template"]
URI_BDD_PRED_OF_VARIANT = NS_MM_BDD["of-variant"]
URI_BDD_PRED_OF_SCENE = NS_MM_BDD["of-scene"]
URI_BDD_PRED_HAS_SCENE = NS_MM_BDD["has-scene"]
URI_BDD_PRED_HAS_CLAUSE = NS_MM_BDD["has-clause"]
URI_BDD_PRED_CLAUSE_OF = NS_MM_BDD["clause-of"]
URI_BDD_PRED_HOLDS_AT = NS_MM_BDD["holds-at"]
URI_BDD_PRED_REF_OBJ = NS_MM_BDD["ref-object"]
URI_BDD_PRED_REF_WS = NS_MM_BDD["ref-workspace"]
URI_BDD_PRED_REF_AGN = NS_MM_BDD["ref-agent"]
URI_BDD_PRED_ELEMS = NS_MM_BDD["elements"]
URI_BDD_PRED_HAS_VARIATION = NS_MM_BDD["has-variation"]
URI_BDD_PRED_VAR_LIST = NS_MM_BDD["variable-list"]
URI_BDD_PRED_REF_VAR = NS_MM_BDD["ref-variable"]
URI_BDD_PRED_ROWS = NS_MM_BDD["rows"]
URI_BDD_PRED_OF_SETS = NS_MM_BDD["of-sets"]
URI_BDD_PRED_IN_SET = NS_MM_BDD["in-set"]
URI_BDD_PRED_HAS_AC = NS_MM_BDD["has-criteria"]
URI_BDD_PRED_HAS_BHV_IMPL = NS_MM_BDD["has-behaviour-impl"]
