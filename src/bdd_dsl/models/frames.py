# SPDX-License-Identifier:  GPL-3.0-or-later
from bdd_dsl.models.uri import (
    URI_TRANS,
    URI_MM_EVENT,
    URI_MM_BT,
    URI_M_CRDN,
)
from bdd_dsl.models.namespace import (
    PREFIX_TRANS,
)
from bdd_dsl.models.queries import (
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
FR_SCENE = "scene"
FR_VARIATIONS = "variations"
FR_VARIABLES = "variables"
FR_OBJECTS = "objects"
FR_WS = "workspaces"
FR_AGENTS = "agents"


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
