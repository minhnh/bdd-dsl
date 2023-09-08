# SPDX-License-Identifier:  GPL-3.0-or-later
from bdd_dsl.models.uri import (
    URI_TRANS,
    URI_MM_GEOM,
    URI_MM_GEOM_REL,
    URI_MM_GEOM_COORD,
    URI_MM_GEOM_EXT,
    URI_MM_PROB,
    URI_MM_BDD,
    URI_MM_EVENT,
    URI_MM_BT,
    URI_M_CRDN,
    URI_M_BDD,
    URI_M_ENV,
    URI_M_AGENT,
    URI_M_SIM,
)
from bdd_dsl.models.queries import (
    Q_PREFIX_TRANS,
    Q_PREFIX_GEOM,
    Q_PREFIX_GEOM_REL,
    Q_PREFIX_GEOM_COORD,
    Q_PREFIX_PROB,
    Q_PREFIX_BDD,
    Q_HAS_VARIATION,
    Q_CAN_BE,
    Q_HAS_AC,
    Q_HAS_BG,
    Q_OF_SCENARIO,
    Q_GIVEN,
    Q_WHEN,
    Q_THEN,
    Q_HAS_CLAUSE,
    Q_HAS_OBJECT,
    Q_HAS_WS,
    Q_HAS_AGENT,
    Q_HAS_EVENT,
    Q_HAS_ROOT,
    Q_HAS_EL_CONN,
    Q_HAS_CHILD,
    Q_HAS_PARENT,
    Q_HAS_START_E,
    Q_HAS_END_E,
    Q_IMPL_MODULE,
    Q_IMPL_CLASS,
    Q_IMPL_ARG_NAME,
    Q_IMPL_ARG_VALUE,
    Q_PREFIX_EVENT,
    Q_PREFIX_BT,
    Q_HAS_SUBTREE,
    Q_PREFIX_ENV,
)
from bdd_dsl.models.urirefs import URI_TRANS_HAS_BODY


FR_NAME = "name"
FR_DATA = "data"
FR_EVENTS = "events"
FR_EL = "event_loop"
FR_ROOT = "root"
FR_SUBTREE = "subtree"
FR_TYPE = "type"
FR_CHILDREN = "children"
FR_HAS_PARENT = "has_parent"
FR_START_E = "start_event"
FR_END_E = "end_event"
FR_IMPL_MODULE = "impl_module"
FR_IMPL_CLASS = "impl_class"
FR_IMPL_ARG_NAMES = "impl_arg_names"
FR_IMPL_ARG_VALS = "impl_arg_values"
FR_CRITERIA = "criteria"
FR_BG = "background"
FR_SCENARIO = "scenario"
FR_GIVEN = "given"
FR_WHEN = "when"
FR_THEN = "then"
FR_CLAUSES = "clauses"
FR_VARIATIONS = "variations"
FR_VARIABLES = "variables"
FR_ENTITIES = "entities"
FR_OBJECTS = "objects"
FR_WS = "workspaces"
FR_AGENTS = "agents"
FR_FLUENT_DATA = "fluent_data"
FR_BODY = "body"
FR_FRAME = "frame"
FR_POSE = "pose"
FR_POSITION = "position"
FR_ORIENTATION = "orientation"
FR_DISTRIBUTION = "distribution"

EVENT_LOOP_FRAME = {
    "@context": {
        "@base": URI_M_CRDN,
        Q_PREFIX_EVENT: URI_MM_EVENT,
        Q_PREFIX_TRANS: URI_TRANS,
        FR_DATA: "@graph",
        FR_NAME: "@id",
        FR_EVENTS: Q_HAS_EVENT,
    },
    FR_DATA: {"@explicit": True, FR_EVENTS: {}},
}

BEHAVIOUR_TREE_FRAME = {
    "@context": {
        "@base": URI_M_CRDN,
        Q_PREFIX_BT: URI_MM_BT,
        Q_PREFIX_TRANS: URI_TRANS,
        FR_DATA: "@graph",
        FR_NAME: "@id",
        FR_TYPE: "@type",
        FR_ROOT: Q_HAS_ROOT,
        FR_SUBTREE: Q_HAS_SUBTREE,
        FR_EL: Q_HAS_EL_CONN,
        FR_EVENTS: Q_HAS_EVENT,
        FR_CHILDREN: Q_HAS_CHILD,
        FR_HAS_PARENT: Q_HAS_PARENT,
        FR_START_E: Q_HAS_START_E,
        FR_END_E: Q_HAS_END_E,
        FR_IMPL_MODULE: Q_IMPL_MODULE,
        FR_IMPL_CLASS: Q_IMPL_CLASS,
        FR_IMPL_ARG_NAMES: Q_IMPL_ARG_NAME,
        FR_IMPL_ARG_VALS: Q_IMPL_ARG_VALUE,
    },
    FR_DATA: {FR_EL: {}},
}

BDD_FRAME = {
    "@context": {
        "@base": URI_M_BDD,
        Q_PREFIX_TRANS: URI_TRANS,
        Q_PREFIX_EVENT: URI_MM_EVENT,
        Q_PREFIX_BDD: URI_MM_BDD,
        Q_PREFIX_ENV: URI_M_ENV,
        "agn": URI_M_AGENT,
        f"{Q_PREFIX_EVENT}m": URI_M_CRDN,
        FR_DATA: "@graph",
        FR_NAME: "@id",
        FR_TYPE: "@type",
        FR_VARIATIONS: Q_HAS_VARIATION,
        FR_ENTITIES: Q_CAN_BE,
        FR_CRITERIA: Q_HAS_AC,
        FR_SCENARIO: Q_OF_SCENARIO,
        FR_BG: Q_HAS_BG,
        FR_GIVEN: Q_GIVEN,
        FR_WHEN: Q_WHEN,
        FR_THEN: Q_THEN,
        FR_CLAUSES: Q_HAS_CLAUSE,
        FR_OBJECTS: Q_HAS_OBJECT,
        FR_WS: Q_HAS_WS,
        FR_AGENTS: Q_HAS_AGENT,
    },
    FR_DATA: {FR_CRITERIA: {}},
}

OBJ_POSE_FRAME = {
    "@context": {
        Q_PREFIX_TRANS: URI_TRANS,
        Q_PREFIX_ENV: URI_M_ENV,
        Q_PREFIX_GEOM: URI_MM_GEOM,
        Q_PREFIX_GEOM_REL: URI_MM_GEOM_REL,
        Q_PREFIX_GEOM_COORD: URI_MM_GEOM_COORD,
        f"{Q_PREFIX_GEOM}-ext": URI_MM_GEOM_EXT,
        Q_PREFIX_PROB: URI_MM_PROB,
        "agn": URI_M_AGENT,
        "sim": URI_M_SIM,
        FR_DATA: "@graph",
        FR_NAME: "@id",
        FR_TYPE: "@type",
    },
    FR_DATA: {URI_TRANS_HAS_BODY.n3(): {}},
}
