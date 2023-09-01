# SPDX-License-Identifier:  GPL-3.0-or-later
from bdd_dsl.models.uri import (
    URI_TRANS,
    URI_MM_BDD,
    URI_MM_EVENT,
    URI_MM_BT,
    URI_MM_PY,
    URI_MM_TASK,
    URI_MM_ENV,
    URI_MM_AGENT,
)

# transformation concepts and relations
Q_PREFIX_TRANS = "trans"
Q_HAS_AC = f"{Q_PREFIX_TRANS}:has-criteria"
Q_OF_SCENARIO = f"{Q_PREFIX_TRANS}:of-scenario"
Q_OF_VARIABLE = f"{Q_PREFIX_TRANS}:of-variable"
Q_HAS_VARIATION = f"{Q_PREFIX_TRANS}:has-variation"
Q_HAS_BG = f"{Q_PREFIX_TRANS}:has-background"
Q_CAN_BE = f"{Q_PREFIX_TRANS}:can-be"
Q_GIVEN = f"{Q_PREFIX_TRANS}:given"
Q_WHEN = f"{Q_PREFIX_TRANS}:when"
Q_THEN = f"{Q_PREFIX_TRANS}:then"
Q_PREDICATE = f"{Q_PREFIX_TRANS}:predicate"
Q_HAS_CLAUSE = f"{Q_PREFIX_TRANS}:has-clause"
Q_HAS_OBJECT = f"{Q_PREFIX_TRANS}:has-object"
Q_HAS_WS = f"{Q_PREFIX_TRANS}:has-workspace"
Q_HAS_AGENT = f"{Q_PREFIX_TRANS}:has-agent"
Q_HAS_EVENT = f"{Q_PREFIX_TRANS}:has-event"
Q_HAS_EL_CONN = f"{Q_PREFIX_TRANS}:has-el-conn"
Q_HAS_ROOT = f"{Q_PREFIX_TRANS}:has-root"
Q_HAS_SUBTREE = f"{Q_PREFIX_TRANS}:has-subtree"
Q_HAS_PARENT = f"{Q_PREFIX_TRANS}:has-parent"
Q_HAS_CHILD = f"{Q_PREFIX_TRANS}:has-child"
Q_HAS_START_E = f"{Q_PREFIX_TRANS}:has-start-event"
Q_HAS_END_E = f"{Q_PREFIX_TRANS}:has-end-event"
Q_IMPL_MODULE = f"{Q_PREFIX_TRANS}:impl-module"
Q_IMPL_CLASS = f"{Q_PREFIX_TRANS}:impl-class"
Q_IMPL_ARG_NAME = f"{Q_PREFIX_TRANS}:impl-arg-name"
Q_IMPL_ARG_VALUE = f"{Q_PREFIX_TRANS}:impl-arg-value"

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

# Task concepts and relations
Q_PREFIX_TASK = "task"
Q_TASK_HAS_VARIATION = f"{Q_PREFIX_TASK}:has-variation"
Q_TASK_CAN_BE = f"{Q_PREFIX_TASK}:can-be"

# Environment concepts and relations
Q_PREFIX_ENV = "env"
Q_ENV_HAS_OBJ = f"{Q_PREFIX_ENV}:has-object"

# Environment concepts and relations
Q_PREFIX_AGENT = "agn"
Q_AGN_HAS_AGENT = f"{Q_PREFIX_AGENT}:has-agent"

# BDD concepts & relations
Q_PREFIX_BDD = "bdd"
Q_BDD_US = f"{Q_PREFIX_BDD}:UserStory"
Q_BDD_SCENARIO = f"{Q_PREFIX_BDD}:Scenario"
Q_BDD_SCENARIO_HAS_OBJ = f"{Q_PREFIX_BDD}:ScenarioHasObjects"
Q_BDD_SCENARIO_HAS_AGN = f"{Q_PREFIX_BDD}:ScenarioHasAgents"
Q_BDD_SCENARIO_VARIANT = f"{Q_PREFIX_BDD}:ScenarioVariant"
Q_BDD_SCENARIO_TASK_VARIABLE = f"{Q_PREFIX_BDD}:ScenarioTaskVariable"
Q_BDD_GIVEN_CLAUSE = f"{Q_PREFIX_BDD}:GivenClause"
Q_BDD_WHEN_CLAUSE = f"{Q_PREFIX_BDD}:WhenClause"
Q_BDD_THEN_CLAUSE = f"{Q_PREFIX_BDD}:ThenClause"
Q_BDD_FLUENT_CLAUSE = f"{Q_PREFIX_BDD}:FluentClause"
Q_BDD_PRED_LOCATED_AT = f"{Q_PREFIX_BDD}:LocatedAtPredicate"
Q_BDD_PRED_IS_NEAR = f"{Q_PREFIX_BDD}:IsNearPredicate"
Q_BDD_PRED_IS_HELD = f"{Q_PREFIX_BDD}:IsHeldPredicate"
Q_BDD_HAS_BG = f"{Q_PREFIX_BDD}:has-background"
Q_BDD_HAS_AC = f"{Q_PREFIX_BDD}:has-criteria"
Q_BDD_OF_SCENARIO = f"{Q_PREFIX_BDD}:of-scenario"
Q_BDD_GIVEN = f"{Q_PREFIX_BDD}:given"
Q_BDD_WHEN = f"{Q_PREFIX_BDD}:when"
Q_BDD_THEN = f"{Q_PREFIX_BDD}:then"
Q_BDD_CLAUSE_OF = f"{Q_PREFIX_BDD}:clause-of"
Q_BDD_OF_CLAUSE = f"{Q_PREFIX_BDD}:of-clause"
Q_BDD_PREDICATE = f"{Q_PREFIX_BDD}:predicate"
Q_BDD_OF_VARIABLE = f"{Q_PREFIX_BDD}:of-variable"
Q_BDD_REF_OBJECT = f"{Q_PREFIX_BDD}:ref-object"
Q_BDD_REF_WS = f"{Q_PREFIX_BDD}:ref-workspace"
Q_BDD_REF_AGENT = f"{Q_PREFIX_BDD}:ref-agent"

# Query for event loops from graph
EVENT_LOOP_QUERY = f"""
PREFIX {Q_PREFIX_EVENT}: <{URI_MM_EVENT}>
PREFIX {Q_PREFIX_TRANS}: <{URI_TRANS}>

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
PREFIX {Q_PREFIX_TRANS}: <{URI_TRANS}>

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

BDD_QUERY = f"""
PREFIX {Q_PREFIX_TRANS}: <{URI_TRANS}>
PREFIX {Q_PREFIX_TASK}: <{URI_MM_TASK}>
PREFIX {Q_PREFIX_ENV}: <{URI_MM_ENV}>
PREFIX {Q_PREFIX_AGENT}: <{URI_MM_AGENT}>
PREFIX {Q_PREFIX_BDD}: <{URI_MM_BDD}>

CONSTRUCT {{
    ?us {Q_HAS_AC} ?scenarioVar .
    ?scenarioVar
        {Q_OF_SCENARIO} ?scenario ;
        {Q_HAS_BG} ?background ;
        {Q_HAS_VARIATION} ?variation .
    ?scenario
        {Q_GIVEN} ?given ;
        {Q_WHEN} ?when ;
        {Q_THEN} ?then .
    ?when {Q_HAS_EVENT} ?event .
    ?background a ?bgType ;
        {Q_HAS_OBJECT} ?scenarioObject ;
        {Q_HAS_AGENT} ?scenarioAgent .
    ?variation
        {Q_OF_VARIABLE} ?variable ;
        {Q_CAN_BE} ?entity .
    ?clauseOrigin {Q_HAS_CLAUSE} ?clause .
    ?clause
        {Q_PREDICATE} ?predicate ;
        {Q_HAS_OBJECT} ?taskObject ;
        {Q_HAS_WS} ?taskWorkspace ;
        {Q_HAS_AGENT} ?taskAgent .
    ?predicate a ?predicateType .
}}
WHERE {{
    ?us a {Q_BDD_US} ;
        {Q_BDD_HAS_AC} ?scenarioVar .
    ?scenarioVar a {Q_BDD_SCENARIO_VARIANT} ;
        {Q_BDD_OF_SCENARIO} ?scenario ;
        {Q_BDD_HAS_BG} ?background ;
        {Q_TASK_HAS_VARIATION} ?variation .

    ?scenario a {Q_BDD_SCENARIO} ;
        {Q_BDD_GIVEN} ?given ;
        {Q_BDD_WHEN} ?when ;
        {Q_BDD_THEN} ?then .

    ?background a ?bgType .
    OPTIONAL {{
        ?background a {Q_BDD_SCENARIO_HAS_OBJ} ;
            {Q_BDD_OF_SCENARIO} ?scenario ;
            {Q_ENV_HAS_OBJ} ?scenarioObject .
    }}
    OPTIONAL {{
        ?background a {Q_BDD_SCENARIO_HAS_AGN} ;
            {Q_BDD_OF_SCENARIO} ?scenario ;
            {Q_AGN_HAS_AGENT} ?scenarioAgent .
    }}

    ?variation
        {Q_BDD_OF_VARIABLE} ?variable ;
        {Q_TASK_CAN_BE} ?entity .

    ?variable a {Q_BDD_SCENARIO_TASK_VARIABLE} .
    ?when a {Q_BDD_WHEN_CLAUSE} .

    OPTIONAL {{ ?when ^{Q_BDD_OF_CLAUSE} / {Q_CRDN_HAS_EVENT} ?event }}

    ?clause a {Q_BDD_FLUENT_CLAUSE} ;
        {Q_BDD_PREDICATE} ?predicate ;
        {Q_BDD_CLAUSE_OF} ?clauseOrigin .
    OPTIONAL {{ ?clause {Q_BDD_REF_OBJECT} ?taskObject }}
    OPTIONAL {{ ?clause {Q_BDD_REF_WS} ?taskWorkspace }}
    OPTIONAL {{ ?clause {Q_BDD_REF_AGENT} ?taskAgent }}

    ?predicate a ?predicateType ;
}}
"""
