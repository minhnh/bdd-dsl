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
from bdd_dsl.models.namespace import (
    PREFIX_GEOM,
    PREFIX_GEOM_REL,
    PREFIX_GEOM_COORD,
    PREFIX_GEOM_EXT,
    PREFIX_PROB,
    PREFIX_ENV,
    PREFIX_TRANS,
    NS_MANAGER,
)
from bdd_dsl.models.queries import (
    Q_PREFIX_BDD,
    Q_BDD_CAN_BE,
    Q_HAS_VARIATION,
    Q_HAS_AC,
    Q_HAS_IN_SCENE,
    Q_OF_SCENARIO,
    Q_GIVEN,
    Q_WHEN,
    Q_THEN,
    Q_BDD_HOLDS,
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
)
from bdd_dsl.models.urirefs import (
    URI_TRANS_HAS_BODY,
    URI_TRANS_HAS_POSE,
    URI_TRANS_HAS_POSITION,
    URI_TRANS_HAS_ORIENTATION,
    URI_TRANS_OF,
    URI_TRANS_WRT,
    URI_TRANS_SAMPLED_FROM,
    URI_TRANS_UPPER,
    URI_TRANS_LOWER,
    URI_TRANS_DIM,
)


FR_NAME = "name"
FR_DATA = "data"
FR_LIST = "list"
FR_OF = "of"
FR_WRT = "wrt"
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
FR_SCENE = "scene"
FR_SCENARIO = "scenario"
FR_GIVEN = "given"
FR_WHEN = "when"
FR_THEN = "then"
FR_HOLDS = "holds"
FR_CLAUSES = "clauses"
FR_VARIATIONS = "variations"
FR_VARIABLES = "variables"
FR_VAR_OBJ = "var_obj"
FR_VAR_WS = "var_ws"
FR_VAR_AGN = "var_agn"
FR_CAN_BE = "can_be"
FR_OBJECTS = "objects"
FR_WS = "workspaces"
FR_AGENTS = "agents"
FR_CLAUSES_DATA = "clauses_data"
FR_FLUENTS = "fluents"
FR_BODY = "body"
FR_FRAME = "frame"
FR_POSE = "pose"
FR_POSITION = "position"
FR_ORIENTATION = "orientation"
FR_DISTRIBUTION = "distribution"
FR_DIM = "dimension"
FR_UPPER = "upper"
FR_LOWER = "lower"


EVENT_LOOP_FRAME = {
    "@context": {
        "@base": URI_M_CRDN,
        Q_PREFIX_EVENT: URI_MM_EVENT,
        PREFIX_TRANS: URI_TRANS,
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
        PREFIX_TRANS: URI_TRANS,
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
        PREFIX_TRANS: URI_TRANS,
        Q_PREFIX_EVENT: URI_MM_EVENT,
        Q_PREFIX_BDD: URI_MM_BDD,
        PREFIX_ENV: URI_M_ENV,
        "agn": URI_M_AGENT,
        f"{Q_PREFIX_EVENT}m": URI_M_CRDN,
        FR_DATA: "@graph",
        FR_NAME: "@id",
        FR_TYPE: "@type",
        FR_VARIATIONS: Q_HAS_VARIATION,
        FR_CAN_BE: Q_BDD_CAN_BE,
        FR_CRITERIA: Q_HAS_AC,
        FR_SCENARIO: Q_OF_SCENARIO,
        FR_SCENE: Q_HAS_IN_SCENE,
        FR_GIVEN: Q_GIVEN,
        FR_WHEN: Q_WHEN,
        FR_THEN: Q_THEN,
        FR_HOLDS: Q_BDD_HOLDS,
        FR_CLAUSES: Q_HAS_CLAUSE,
        FR_OBJECTS: Q_HAS_OBJECT,
        FR_WS: Q_HAS_WS,
        FR_AGENTS: Q_HAS_AGENT,
    },
    FR_DATA: {FR_CRITERIA: {}},
}

OBJ_POSE_FRAME = {
    "@context": {
        PREFIX_TRANS: URI_TRANS,
        PREFIX_ENV: URI_M_ENV,
        PREFIX_GEOM: URI_MM_GEOM,
        PREFIX_GEOM_REL: URI_MM_GEOM_REL,
        PREFIX_GEOM_COORD: URI_MM_GEOM_COORD,
        PREFIX_GEOM_EXT: URI_MM_GEOM_EXT,
        PREFIX_PROB: URI_MM_PROB,
        "agn": URI_M_AGENT,
        "sim": URI_M_SIM,
        FR_DATA: "@graph",
        FR_NAME: "@id",
        FR_TYPE: "@type",
        FR_LIST: "@list",
        FR_BODY: URI_TRANS_HAS_BODY.n3(NS_MANAGER),
        FR_POSE: URI_TRANS_HAS_POSE.n3(NS_MANAGER),
        FR_POSITION: URI_TRANS_HAS_POSITION.n3(NS_MANAGER),
        FR_ORIENTATION: URI_TRANS_HAS_ORIENTATION.n3(NS_MANAGER),
        FR_OF: URI_TRANS_OF.n3(NS_MANAGER),
        FR_WRT: URI_TRANS_WRT.n3(NS_MANAGER),
        FR_DISTRIBUTION: URI_TRANS_SAMPLED_FROM.n3(NS_MANAGER),
        FR_DIM: URI_TRANS_DIM.n3(NS_MANAGER),
        FR_UPPER: URI_TRANS_UPPER.n3(NS_MANAGER),
        FR_LOWER: URI_TRANS_LOWER.n3(NS_MANAGER),
    },
    FR_DATA: {FR_BODY: {}},
}
