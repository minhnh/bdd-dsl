# SPDX-License-Identifier:  GPL-3.0-or-later
from rdf_utils.uri import URL_SECORO_M
from bdd_dsl.models.namespace import PREFIX_TRANS
from bdd_dsl.models.uri import (
    URI_TRANS,
    URI_MM_EVENT,
    URI_MM_BT,
    URI_MM_PY,
)
from bdd_dsl.models.urirefs import (
    URI_AGN_PRED_HAS_AGN_MODEL,
    URI_AGN_PRED_OF_AGN,
    URI_AGN_TYPE_AGN,
    URI_AGN_TYPE_AGN_MODEL,
    URI_AGN_TYPE_MOD_AGN,
    URI_BDD_PRED_GIVEN,
    URI_BDD_PRED_HAS_AC,
    URI_BDD_PRED_HAS_SCENE,
    URI_BDD_PRED_HAS_VARIATION,
    URI_BDD_PRED_OF_SCENARIO,
    URI_BDD_PRED_OF_SCENE,
    URI_BDD_PRED_OF_TMPL,
    URI_BDD_PRED_THEN,
    URI_BDD_PRED_WHEN,
    URI_BDD_TYPE_TASK_VAR,
    URI_BHV_TYPE_BHV,
    URI_ENV_TYPE_OBJ,
    URI_ENV_PRED_HAS_OBJ_MODEL,
    URI_ENV_TYPE_OBJ_MODEL,
    URI_ENV_TYPE_MOD_OBJ,
    URI_SIM_PRED_HAS_CONFIG,
    URI_TASK_TYPE_TASK,
    URI_BDD_TYPE_SCENARIO,
    URI_BDD_TYPE_SCENARIO_TMPL,
    URI_BDD_TYPE_SCENARIO_VARIANT,
    URI_BDD_TYPE_US,
    URI_BHV_PRED_OF_BHV,
    URI_TASK_PRED_OF_TASK,
    URI_GEOM_RIGID_BODY,
    URI_GEOM_SIMPLICES,
    URI_GEOM_FRAME,
    URI_GEOM_POSE,
    URI_GEOM_OF,
    URI_GEOM_WRT,
    URI_GEOM_POSE_COORD,
    URI_GEOM_POSITION_COORD,
    URI_GEOM_ORIENTATION_COORD,
    URI_GEOM_OF_POSE,
    URI_GEOM_OF_POSITION,
    URI_GEOM_OF_ORIENTATION,
    URI_GEOM_POSE_FROM_POS_ORN,
    URI_PROB_SAMPLED_QUANTITY,
    URI_PROB_UNIFORM,
    URI_PROB_DIM,
    URI_PROB_LOWER,
    URI_PROB_UPPER,
    URI_PROB_FROM_DISTRIBUTION,
    URI_ENV_PRED_OF_OBJ,
    URI_TRANS_HAS_BODY,
    URI_TRANS_HAS_POSE,
    URI_TRANS_HAS_POSITION,
    URI_TRANS_HAS_ORIENTATION,
    URI_TRANS_OF,
    URI_TRANS_WRT,
    URI_TRANS_SAMPLED_FROM,
    URI_TRANS_DIM,
    URI_TRANS_UPPER,
    URI_TRANS_LOWER,
)

# URLs to public queries
URL_Q_BDD_US = f"{URL_SECORO_M}/acceptance-criteria/bdd/queries/user-story.rq"

# transformation concepts and relations
Q_HAS_EVENT = f"{PREFIX_TRANS}:has-event"
Q_HAS_EL_CONN = f"{PREFIX_TRANS}:has-el-conn"
Q_HAS_ROOT = f"{PREFIX_TRANS}:has-root"
Q_HAS_SUBTREE = f"{PREFIX_TRANS}:has-subtree"
Q_HAS_PARENT = f"{PREFIX_TRANS}:has-parent"
Q_HAS_CHILD = f"{PREFIX_TRANS}:has-child"
Q_HAS_START_E = f"{PREFIX_TRANS}:has-start-event"
Q_HAS_END_E = f"{PREFIX_TRANS}:has-end-event"
Q_IMPL_MODULE = f"{PREFIX_TRANS}:impl-module"
Q_IMPL_CLASS = f"{PREFIX_TRANS}:impl-class"
Q_IMPL_ARG_NAME = f"{PREFIX_TRANS}:impl-arg-name"
Q_IMPL_ARG_VALUE = f"{PREFIX_TRANS}:impl-arg-value"

# coordination concepts & relations
Q_PREFIX_EVENT = "evt"
Q_CRDN_EVENT_LOOP = f"{Q_PREFIX_EVENT}:EventLoop"
Q_CRDN_EVENT_LOOP_CONN = f"{Q_PREFIX_EVENT}:EventLoopConn"
Q_CRDN_HAS_EL_CONN = f"{Q_PREFIX_EVENT}:event-loop-connection"
Q_CRDN_OF_EL = f"{Q_PREFIX_EVENT}:event-loop"
Q_CRDN_HAS_EVENT = f"{Q_PREFIX_EVENT}:has-event"

# behaviour tree concepts & relations
Q_PREFIX_BT = "bt"
Q_BT_WITH_EVENTS = f"{Q_PREFIX_BT}:BehaviourTreeWithEvents"
Q_BT_USES_IMPL = f"{Q_PREFIX_BT}:uses-implementation"
Q_BT_SEQUENCE = f"{Q_PREFIX_BT}:Sequence"
Q_BT_PARALLEL = f"{Q_PREFIX_BT}:Parallel"
Q_BT_ACTION = f"{Q_PREFIX_BT}:Action"
Q_BT_ACTION_IMPL = f"{Q_PREFIX_BT}:PythonActionImpl"
Q_BT_ACTION_SUBTREE = f"{Q_PREFIX_BT}:ActionSubtree"
Q_BT_SUBTREE_IMPL = f"{Q_PREFIX_BT}:SubtreeImpl"
Q_BT_OF_SUBTREE = f"{Q_PREFIX_BT}:of-subtree"
Q_BT_SUBROOT = f"{Q_PREFIX_BT}:subroot"
Q_BT_PARENT = f"{Q_PREFIX_BT}:parent"
Q_BT_CHILDREN = f"{Q_PREFIX_BT}:has-child"
Q_BT_OF_ACTION = f"{Q_PREFIX_BT}:of-action"
Q_BT_START_E = f"{Q_PREFIX_BT}:start-event"
Q_BT_END_E = f"{Q_PREFIX_BT}:end-event"

# Python concepts & relations
Q_PREFIX_PY = "py"
Q_PY_MODULE = f"{Q_PREFIX_PY}:module"
Q_PY_CLASS = f"{Q_PREFIX_PY}:class-name"
Q_PY_ARG_NAME = f"{Q_PREFIX_PY}:ArgName"
Q_PY_ARG_VAL = f"{Q_PREFIX_PY}:ArgValue"

# BDD concepts & relations
Q_PREFIX_BDD = "mm_bdd"
Q_BDD_US = f"{Q_PREFIX_BDD}:UserStory"
Q_BDD_SCENARIO = f"{Q_PREFIX_BDD}:Scenario"
Q_BDD_SCENE_HAS_OBJ = f"{Q_PREFIX_BDD}:SceneHasObjects"
Q_BDD_SCENE_HAS_AGN = f"{Q_PREFIX_BDD}:SceneHasAgents"
Q_BDD_SCENARIO_VARIANT = f"{Q_PREFIX_BDD}:ScenarioVariant"
Q_BDD_SCENARIO_TASK_VARIABLE = f"{Q_PREFIX_BDD}:ScenarioTaskVariable"
Q_BDD_GIVEN_CLAUSE = f"{Q_PREFIX_BDD}:GivenClause"
Q_BDD_WHEN_CLAUSE = f"{Q_PREFIX_BDD}:WhenClause"
Q_BDD_THEN_CLAUSE = f"{Q_PREFIX_BDD}:ThenClause"
Q_BDD_FLUENT_CLAUSE = f"{Q_PREFIX_BDD}:FluentClause"
Q_BDD_PRED_LOCATED_AT = f"{Q_PREFIX_BDD}:LocatedAtPredicate"
Q_BDD_PRED_IS_NEAR = f"{Q_PREFIX_BDD}:IsNearPredicate"
Q_BDD_PRED_IS_HELD = f"{Q_PREFIX_BDD}:IsHeldPredicate"
Q_BDD_HAS_IN_SCENE = f"{Q_PREFIX_BDD}:has-in-scene"
Q_BDD_HAS_AC = f"{Q_PREFIX_BDD}:has-criteria"
Q_BDD_OF_SCENARIO = f"{Q_PREFIX_BDD}:of-scenario"
Q_BDD_GIVEN = f"{Q_PREFIX_BDD}:given"
Q_BDD_WHEN = f"{Q_PREFIX_BDD}:when"
Q_BDD_THEN = f"{Q_PREFIX_BDD}:then"
Q_BDD_CLAUSE_OF = f"{Q_PREFIX_BDD}:clause-of"
Q_BDD_OF_CLAUSE = f"{Q_PREFIX_BDD}:of-clause"
Q_BDD_HOLDS = f"{Q_PREFIX_BDD}:holds"
Q_BDD_OF_VARIABLE = f"{Q_PREFIX_BDD}:of-variable"
Q_BDD_REF_OBJECT = f"{Q_PREFIX_BDD}:ref-object"
Q_BDD_REF_WS = f"{Q_PREFIX_BDD}:ref-workspace"
Q_BDD_REF_AGENT = f"{Q_PREFIX_BDD}:ref-agent"

# Query for event loops from graph
EVENT_LOOP_QUERY = f"""
PREFIX {Q_PREFIX_EVENT}: <{URI_MM_EVENT}>
PREFIX {PREFIX_TRANS}: <{URI_TRANS}>

CONSTRUCT {{
    ?eventLoopConn {Q_HAS_EVENT} ?event .
}}
WHERE {{
    ?eventLoopConn a {Q_CRDN_EVENT_LOOP_CONN} ;
        {Q_CRDN_OF_EL} ?eventLoop ;
        {Q_CRDN_HAS_EVENT} ?event .
    ?eventLoop a {Q_CRDN_EVENT_LOOP} .
}}
"""

BEHAVIOUR_TREE_QUERY = f"""
PREFIX {Q_PREFIX_BT}: <{URI_MM_BT}>
PREFIX {Q_PREFIX_PY}: <{URI_MM_PY}>
PREFIX {PREFIX_TRANS}: <{URI_TRANS}>

CONSTRUCT {{
    ?rootImpl
        {Q_HAS_EL_CONN} ?elConn ;
        {Q_HAS_SUBTREE} ?rootChildImpl .
    ?subtreeImpl a ?compositeType ;
        {Q_HAS_CHILD} ?childImpl .
    ?childImpl
        {Q_HAS_START_E} ?startEvent ;
        {Q_HAS_END_E} ?endEvent ;
        {Q_IMPL_MODULE} ?implModule ;
        {Q_IMPL_CLASS} ?implClass ;
        {Q_IMPL_ARG_NAME} ?implArgNames ;
        {Q_IMPL_ARG_VALUE} ?implArgValues .
    ?elConn {Q_HAS_EVENT} ?event .
}}
WHERE {{
    ?subtreeImpl a {Q_BT_SUBTREE_IMPL} ;
        {Q_BT_USES_IMPL} ?childImpl ;
        {Q_BT_OF_SUBTREE} ?subtree .
    ?subtree a {Q_BT_ACTION_SUBTREE} ;
        {Q_BT_PARENT} ?subtreeRootAction ;
        {Q_BT_SUBROOT} ?subtreeComposite .
    ?subtreeComposite a ?compositeType ;
        {Q_BT_CHILDREN} ?childRootAction .

    OPTIONAL {{
        ?subtreeImpl ^{Q_BT_USES_IMPL} ?rootImpl .
        ?subtree {Q_BT_PARENT} ?root ;
            {Q_BT_SUBROOT} ?rootComposite .
        ?rootImpl a {Q_BT_WITH_EVENTS} ;
            {Q_CRDN_HAS_EL_CONN} ?elConn ;
            {Q_BT_USES_IMPL} ?rootChildImpl .
        ?elConn a {Q_CRDN_EVENT_LOOP_CONN} ;
            {Q_CRDN_HAS_EVENT} ?event .
    }}

    OPTIONAL {{
        ?childImpl a {Q_BT_SUBTREE_IMPL} ;
            {Q_BT_OF_SUBTREE} ?childSubtree .
        ?childSubtree a {Q_BT_ACTION_SUBTREE} ;
            {Q_BT_PARENT} ?childRootAction ;
            {Q_BT_SUBROOT} ?childComposite .
    }}

    OPTIONAL {{
        ?childImpl a {Q_BT_ACTION_IMPL} ;
            {Q_BT_OF_ACTION} ?childAction ;
            {Q_PY_MODULE} ?implModule ;
            {Q_PY_CLASS} ?implClass .
        ?childAction a {Q_BT_ACTION} ;
            ^{Q_BT_OF_ACTION} / {Q_BT_START_E} ?startEvent ;
            ^{Q_BT_OF_ACTION} / {Q_BT_END_E} ?endEvent .
        OPTIONAL {{
            ?childImpl {Q_PY_ARG_NAME} ?implArgNames ;
                {Q_PY_ARG_VAL} ?implArgValues .
        }}
    }}

}}
"""

OBJ_POSE_COORD_QUERY = f"""
prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

CONSTRUCT {{
    ?obj {URI_TRANS_HAS_BODY.n3()} ?body .
    ?body
        {URI_TRANS_HAS_POSE.n3()} ?pose .
    ?pose a ?poseCoordType ;
        {URI_TRANS_OF.n3()} ?frame ;
        {URI_TRANS_WRT.n3()} ?poseOriginFrame ;
        {URI_TRANS_HAS_POSITION.n3()} ?posePosition ;
        {URI_TRANS_HAS_ORIENTATION.n3()} ?poseOrientation .
    ?posePosition a ?positionCoordType ;
        {URI_TRANS_SAMPLED_FROM.n3()} ?positionDistr .
    ?positionDistr a ?positionDistrType ;
        {URI_TRANS_DIM.n3()} ?positionDistrDim ;
        {URI_TRANS_LOWER.n3()} ?positionDistrLowerList ;
        {URI_TRANS_UPPER.n3()} ?positionDistrUpperList .
    ?positionDistrLowerListRest
        rdf:first ?positionDistrLowerListHead ;
        rdf:rest ?positionDistrLowerListTail .
    ?positionDistrUpperListRest
        rdf:first ?positionDistrUpperListHead ;
        rdf:rest ?positionDistrUpperListTail .
    ?poseOrientation a ?orientationCoordType ;
        {URI_TRANS_SAMPLED_FROM.n3()} ?orientationDistr .
    ?orientationDistr a ?orientationDistrType .
}}
WHERE {{
    ?body a {URI_GEOM_RIGID_BODY.n3()} ;
        {URI_ENV_PRED_OF_OBJ.n3()} ?obj ;
        {URI_GEOM_SIMPLICES.n3()} ?frame .
    ?frame a {URI_GEOM_FRAME.n3()} ;
        ^{URI_GEOM_OF.n3()} ?pose .
    ?pose a {URI_GEOM_POSE.n3()} ;
        {URI_GEOM_WRT.n3()} ?poseOriginFrame ;
        ^{URI_GEOM_OF_POSE.n3()} ?poseCoord .
    ?poseCoord a {URI_GEOM_POSE_COORD.n3()} ;
        a ?poseCoordType .
    OPTIONAL {{
        ?poseCoord a {URI_GEOM_POSE_FROM_POS_ORN.n3()} ;
            {URI_GEOM_OF_POSITION.n3()} ?posePosition ;
            {URI_GEOM_OF_ORIENTATION.n3()} ?poseOrientation .

        ?posePosition ^{URI_GEOM_OF_POSITION.n3()} ?positionCoord .
        ?positionCoord a {URI_GEOM_POSITION_COORD.n3()} ;
            a ?positionCoordType .
        OPTIONAL {{
            ?positionCoord a {URI_PROB_SAMPLED_QUANTITY.n3()} ;
                {URI_PROB_FROM_DISTRIBUTION.n3()} ?positionDistr .
            ?positionDistr a ?positionDistrType .
            OPTIONAL {{ ?positionDistr {URI_PROB_DIM.n3()} ?positionDistrDim }}
            OPTIONAL {{
                ?positionDistr a {URI_PROB_UNIFORM.n3()} ;
                    {URI_PROB_LOWER.n3()} ?positionDistrLowerList ;
                    {URI_PROB_UPPER.n3()} ?positionDistrUpperList .
                ?positionDistrLowerList rdf:rest* ?positionDistrLowerListRest .
                ?positionDistrLowerListRest rdf:first ?positionDistrLowerListHead ;
                    rdf:rest ?positionDistrLowerListTail .
                ?positionDistrUpperList rdf:rest* ?positionDistrUpperListRest .
                ?positionDistrUpperListRest rdf:first ?positionDistrUpperListHead ;
                    rdf:rest ?positionDistrUpperListTail .
            }}
        }}

        ?poseOrientation ^{URI_GEOM_OF_ORIENTATION.n3()} ?orientationCoord .
        ?orientationCoord a {URI_GEOM_ORIENTATION_COORD.n3()} ;
            a ?orientationCoordType .
        OPTIONAL {{
            ?orientationCoord a {URI_PROB_SAMPLED_QUANTITY.n3()} ;
                {URI_PROB_FROM_DISTRIBUTION.n3()} ?orientationDistr .
            ?orientationDistr a ?orientationDistrType .
        }}
    }}
}}
"""

Q_USER_STORY = f"""
CONSTRUCT {{
    ?us a ?usType ;
        {URI_BDD_PRED_HAS_AC.n3()} ?scenarioVar .
    ?scenarioVar a ?scenarioVarType ;
        {URI_BDD_PRED_HAS_VARIATION.n3()} ?taskVariation ;
        {URI_BDD_PRED_HAS_SCENE.n3()} ?scene ;
        {URI_BDD_PRED_OF_TMPL.n3()} ?scenarioTmpl ;
        {URI_BDD_PRED_OF_SCENARIO.n3()} ?scenario .
    ?scenario a {URI_BDD_TYPE_SCENARIO.n3()} ;
        {URI_BHV_PRED_OF_BHV.n3()} ?behaviour ;
        {URI_TASK_PRED_OF_TASK.n3()} ?task ;
        {URI_BDD_PRED_GIVEN.n3()} ?given ;
        {URI_BDD_PRED_WHEN.n3()} ?when ;
        {URI_BDD_PRED_THEN.n3()} ?then .
    ?taskVariation a ?varType ;
        {URI_TASK_PRED_OF_TASK.n3()} ?task .
    ?scene {URI_BDD_PRED_HAS_SCENE.n3()} ?sceneElem .
    ?sceneElem a ?sceneElemType .
}}
WHERE {{
    ?us a {URI_BDD_TYPE_US.n3()} ;
        a ?usType ;
        {URI_BDD_PRED_HAS_AC.n3()} ?scenarioVar .

    ?scenarioVar a {URI_BDD_TYPE_SCENARIO_VARIANT.n3()} ;
        a ?scenarioVarType ;
        {URI_BDD_PRED_OF_TMPL.n3()} ?scenarioTmpl ;
        {URI_BDD_PRED_HAS_SCENE.n3()} ?sceneElem ;
        {URI_BDD_PRED_HAS_VARIATION.n3()} ?taskVariation .

    ?scenarioTmpl a {URI_BDD_TYPE_SCENARIO_TMPL.n3()} ;
        {URI_BDD_PRED_HAS_SCENE.n3()} ?scene ;
        {URI_BDD_PRED_OF_SCENARIO.n3()} ?scenario .

    ?sceneElem a ?sceneElemType ;
        {URI_BDD_PRED_OF_SCENE.n3()} ?scene .

    ?scenario a {URI_BDD_TYPE_SCENARIO.n3()} ;
        {URI_BHV_PRED_OF_BHV.n3()} ?behaviour ;
        {URI_TASK_PRED_OF_TASK.n3()} ?task ;
        {URI_BDD_PRED_GIVEN.n3()} ?given ;
        {URI_BDD_PRED_WHEN.n3()} ?when ;
        {URI_BDD_PRED_THEN.n3()} ?then .

    ?taskVariation a {URI_BDD_TYPE_TASK_VAR.n3()} ;
        a ?varType ;
        {URI_TASK_PRED_OF_TASK.n3()} ?task .

    ?behaviour a {URI_BHV_TYPE_BHV.n3()} .
    ?task a {URI_TASK_TYPE_TASK.n3()} .
}}
"""

Q_MODELLED_OBJECT = f"""
CONSTRUCT {{
    ?obj a ?objType ;
        {URI_ENV_PRED_HAS_OBJ_MODEL.n3()} ?objModel ;
        {URI_SIM_PRED_HAS_CONFIG.n3()} ?configs .
    ?objModel a ?objModelType .
}}
WHERE {{
    ?modelledObj a {URI_ENV_TYPE_MOD_OBJ.n3()} ;
        {URI_ENV_PRED_HAS_OBJ_MODEL.n3()} ?objModel ;
        {URI_ENV_PRED_OF_OBJ.n3()} ?obj ;
        {URI_SIM_PRED_HAS_CONFIG.n3()} ?configs .
    ?obj a {URI_ENV_TYPE_OBJ.n3()} ;
        a ?objType .

    ?objModel a {URI_ENV_TYPE_OBJ_MODEL.n3()} ;
        a ?objModelType .
}}
"""

Q_MODELLED_AGENT = f"""
CONSTRUCT {{
    ?agn a ?agnType ;
        {URI_AGN_PRED_HAS_AGN_MODEL.n3()} ?agnModel ;
        {URI_SIM_PRED_HAS_CONFIG.n3()} ?configs .
    ?agnModel a ?agnModelType .
}}
WHERE {{
    ?modelledAgn a {URI_AGN_TYPE_MOD_AGN.n3()} ;
        {URI_AGN_PRED_HAS_AGN_MODEL.n3()} ?agnModel ;
        {URI_AGN_PRED_OF_AGN.n3()} ?agn ;
        {URI_SIM_PRED_HAS_CONFIG.n3()} ?configs .
    ?agn a {URI_AGN_TYPE_AGN.n3()} ;
        a ?agnType .

    ?agnModel a {URI_AGN_TYPE_AGN_MODEL.n3()} ;
        a ?agnModelType .
}}
"""
