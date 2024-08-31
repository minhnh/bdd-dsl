# SPDX-License-Identifier:  GPL-3.0-or-later
from rdf_utils.namespace import (
    NS_MM_GEOM,
    NS_MM_GEOM_REL,
    NS_MM_GEOM_COORD,
    NS_MM_ENV,
    NS_MM_AGN,
    NS_MM_TIME,
)
from bdd_dsl.models.namespace import (
    NS_MM_BDD,
    NS_MM_BHV,
    NS_MM_SIM,
    NS_MM_TASK,
    NS_TRANS,
    NS_MM_GEOM_EXT,
    NS_MM_PROB,
    NS_MM_DISTRIB,
)

# Transformation
URI_TRANS_HAS_BODY = NS_TRANS["has-body"]
URI_TRANS_HAS_POSE = NS_TRANS["has-pose"]
URI_TRANS_HAS_POSITION = NS_TRANS["has-position"]
URI_TRANS_HAS_ORIENTATION = NS_TRANS["has-orientation"]
URI_TRANS_OF = NS_TRANS["of"]
URI_TRANS_WRT = NS_TRANS["with-respect-to"]
URI_TRANS_SAMPLED_FROM = NS_TRANS["sampled-from"]
URI_TRANS_DIM = NS_TRANS["dimension"]
URI_TRANS_UPPER = NS_TRANS["upper-bound"]
URI_TRANS_LOWER = NS_TRANS["lower-bound"]

# Geometry structural entities
URI_GEOM_POINT = NS_MM_GEOM["Point"]
URI_GEOM_FRAME = NS_MM_GEOM["Frame"]
URI_GEOM_RIGID_BODY = NS_MM_GEOM["RigidBody"]
URI_GEOM_SIMPLICES = NS_MM_GEOM["simplices"]

# Geometry spatial relations
URI_GEOM_POSITION = NS_MM_GEOM_REL["Position"]
URI_GEOM_ORIENTATION = NS_MM_GEOM_REL["Orientation"]
URI_GEOM_POSE = NS_MM_GEOM_REL["Pose"]
URI_GEOM_OF = NS_MM_GEOM_REL["of"]
URI_GEOM_WRT = NS_MM_GEOM_REL["with-respect-to"]

# Geometry coordinates
URI_GEOM_POSE_COORD = NS_MM_GEOM_COORD["PoseCoordinate"]
URI_GEOM_POSITION_COORD = NS_MM_GEOM_COORD["PositionCoordinate"]
URI_GEOM_ORIENTATION_COORD = NS_MM_GEOM_COORD["OrientationCoordinate"]
URI_GEOM_POSE_REF = NS_MM_GEOM_COORD["PoseReference"]
URI_GEOM_POSITION_REF = NS_MM_GEOM_COORD["PositionReference"]
URI_GEOM_ORIENTATION_REF = NS_MM_GEOM_COORD["OrientationReference"]
URI_GEOM_OF_POSE = NS_MM_GEOM_COORD["of-pose"]
URI_GEOM_OF_POSITION = NS_MM_GEOM_COORD["of-position"]
URI_GEOM_OF_ORIENTATION = NS_MM_GEOM_COORD["of-orientation"]

# Geometry extension
URI_GEOM_POSE_FROM_POS_ORN = NS_MM_GEOM_EXT["PoseFromPositionOrientation"]
URI_GEOM_QUATERNION = NS_MM_GEOM_EXT["Quaternion"]
URI_GEOM_ROTATION_MATRIX = NS_MM_GEOM_EXT["RotationMatrix"]
URI_GEOM_EULER_ANGLES = NS_MM_GEOM_EXT["EulerAngles"]
URI_GEOM_FROM_POSITION = NS_MM_GEOM_EXT["from-position"]
URI_GEOM_FROM_ORIENTATION = NS_MM_GEOM_EXT["from-orientation"]

# Distribution
URI_DISTRIB_SAMPLED_QUANTITY = NS_MM_DISTRIB["SampledQuantity"]
URI_DISTRIB_UNIFORM = NS_MM_DISTRIB["Uniform"]
URI_DISTRIB_CONTINUOUS = NS_MM_DISTRIB["Continuous"]
URI_DISTRIB_UNIFORM_ROTATION = NS_MM_DISTRIB["UniformRotation"]
URI_DISTRIB_FROM_DISTRIBUTION = NS_MM_DISTRIB["from-distribution"]
URI_DISTRIB_DIM = NS_MM_DISTRIB["dimension"]
URI_DISTRIB_UPPER = NS_MM_DISTRIB["upper-bound"]
URI_DISTRIB_LOWER = NS_MM_DISTRIB["lower-bound"]

# Probability
URI_PROB_SAMPLED_QUANTITY = NS_MM_PROB["SampledQuantity"]
URI_PROB_DISCRETE = NS_MM_PROB["Discrete"]
URI_PROB_CONTINUOUS = NS_MM_PROB["Continuous"]
URI_PROB_UNIFORM = NS_MM_PROB["Uniform"]
URI_PROB_UNIFORM_ROTATION = NS_MM_PROB["UniformRotation"]
URI_PROB_DIM = NS_MM_PROB["dimension"]
URI_PROB_LOWER = NS_MM_PROB["lower-bound"]
URI_PROB_UPPER = NS_MM_PROB["upper-bound"]
URI_PROB_FROM_DISTRIBUTION = NS_MM_PROB["from-distribution"]

# Environment
URI_ENV_TYPE_OBJ = NS_MM_ENV["Object"]
URI_ENV_TYPE_WS = NS_MM_ENV["Workspace"]
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
URI_AGN_PRED_OF_AGN = NS_MM_AGN["of-agent"]
URI_AGN_PRED_HAS_AGN = NS_MM_AGN["has-agent"]

# Behaviour
URI_BHV_TYPE_BHV = NS_MM_BHV["Behaviour"]
URI_BHV_PRED_OF_BHV = NS_MM_BHV["of-behaviour"]

# Time
URI_TIME_TYPE_BEFORE_EVT = NS_MM_TIME["BeforeEventConstraint"]
URI_TIME_TYPE_AFTER_EVT = NS_MM_TIME["AfterEventConstraint"]
URI_TIME_PRED_REF_EVT = NS_MM_TIME["ref-event"]

# Task
URI_TASK_TYPE_TASK = NS_MM_TASK["Task"]
URI_TASK_PRED_OF_TASK = NS_MM_TASK["of-task"]

# Simulation
URI_SIM_TYPE_SYS_RES = NS_MM_SIM["SystemResource"]
URI_SIM_PRED_HAS_CONFIG = NS_MM_SIM["has-config"]
URI_SIM_PRED_PATH = NS_MM_SIM["path"]

# BDD
URI_BDD_TYPE_US = NS_MM_BDD["UserStory"]
URI_BDD_TYPE_SCENARIO = NS_MM_BDD["Scenario"]
URI_BDD_TYPE_SCENARIO_TMPL = NS_MM_BDD["ScenarioTemplate"]
URI_BDD_TYPE_SCENARIO_VARIANT = NS_MM_BDD["ScenarioVariant"]
URI_BDD_TYPE_SCENE = NS_MM_BDD["Scene"]
URI_BDD_TYPE_SCENE_OBJ = NS_MM_BDD["SceneHasObjects"]
URI_BDD_TYPE_SCENE_WS = NS_MM_BDD["SceneHasWorkspaces"]
URI_BDD_TYPE_SCENE_AGN = NS_MM_BDD["SceneHasAgents"]
URI_BDD_TYPE_FLUENT = NS_MM_BDD["Fluent"]
URI_BDD_TYPE_FLUENT_CLAUSE = NS_MM_BDD["FluentClause"]
URI_BDD_TYPE_LOCATED_AT = NS_MM_BDD["LocatedAtPredicate"]
URI_BDD_TYPE_IS_HELD = NS_MM_BDD["IsHeldPredicate"]
URI_BDD_TYPE_SCENARIO_EXEC = NS_MM_BDD["ScenarioExecution"]
URI_BDD_TYPE_BHV_IMPL = NS_MM_BDD["BehaviourImplementation"]
URI_BDD_PRED_GIVEN = NS_MM_BDD["given"]
URI_BDD_PRED_WHEN = NS_MM_BDD["when"]
URI_BDD_PRED_THEN = NS_MM_BDD["then"]
URI_BDD_PRED_OF_SCENARIO = NS_MM_BDD["of-scenario"]
URI_BDD_PRED_OF_TMPL = NS_MM_BDD["of-template"]
URI_BDD_PRED_OF_SCENE = NS_MM_BDD["of-scene"]
URI_BDD_PRED_HAS_SCENE = NS_MM_BDD["has-scene"]
URI_BDD_PRED_HAS_CLAUSE = NS_MM_BDD["has-clause"]
URI_BDD_PRED_CLAUSE_OF = NS_MM_BDD["clause-of"]
URI_BDD_PRED_HOLDS = NS_MM_BDD["holds"]
URI_BDD_PRED_HOLDS_AT = NS_MM_BDD["holds-at"]
URI_BDD_PRED_REF_OBJ = NS_MM_BDD["ref-object"]
URI_BDD_PRED_REF_WS = NS_MM_BDD["ref-workspace"]
URI_BDD_PRED_REF_AGN = NS_MM_BDD["ref-agent"]
URI_BDD_PRED_HAS_VARIATION = NS_MM_BDD["has-variation"]
URI_BDD_PRED_HAS_AC = NS_MM_BDD["has-criteria"]
URI_BDD_PRED_HAS_BHV_IMPL = NS_MM_BDD["has-behaviour-impl"]
