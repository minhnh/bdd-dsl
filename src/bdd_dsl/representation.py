# SPDX-License-Identifier:  GPL-3.0-or-later
from numbers import Number
from typing import Any, Iterable, Optional, Protocol
from rdf_utils.models.common import ModelBase
from rdflib import URIRef
from rdflib.namespace import NamespaceManager

from bdd_dsl.models.clauses import FluentClauseModel, WhenBehaviourModel
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_REF_AGN,
    URI_BDD_PRED_REF_OBJ,
    URI_BDD_PRED_REF_WS,
    URI_BDD_TYPE_IS_HELD,
    URI_BDD_TYPE_LOCATED_AT,
    URI_BHV_PRED_TARGET_AGN,
    URI_BHV_PRED_TARGET_OBJ,
    URI_BHV_PRED_TARGET_WS,
    URI_BHV_TYPE_PICK,
    URI_BHV_TYPE_PLACE,
    URI_TIME_PRED_AFTER_EVT,
    URI_TIME_PRED_BEFORE_EVT,
)


def var_val_to_str(var_val: Any, ns_manager: Optional[NamespaceManager] = None) -> str:
    if isinstance(var_val, URIRef):
        return var_val.n3(namespace_manager=ns_manager)

    if isinstance(var_val, str):
        return var_val

    if isinstance(var_val, Number):
        return str(var_val)

    if isinstance(var_val, Iterable):
        uri_str_list = []
        for uri in var_val:
            assert isinstance(uri, URIRef), f"not an Iterable of URIRef: {var_val}"
            uri_str_list.append(uri.n3(namespace_manager=ns_manager))

        return str(uri_str_list)

    raise RuntimeError(f"var_val_to_str: unhandled types: (type={type(var_val)}) {var_val}")


def get_model_rep(
    model: ModelBase,
    tmpl_str: str,
    attr_mappings: dict[URIRef, str],
    ns_manager: Optional[NamespaceManager] = None,
) -> str:
    subs = {}
    for attr_uri, sub_key in attr_mappings.items():
        assert sub_key not in subs, (
            f"duplicate substitute key when generating rep for {model.id.n3(ns_manager)}: {sub_key}"
        )
        attr = model.get_attr(key=attr_uri)
        assert attr is not None, (
            f"'{model.id.n3(ns_manager)}' doesn't have attribute '{attr_uri.n3(ns_manager)}'"
        )
        subs[sub_key] = var_val_to_str(var_val=attr, ns_manager=ns_manager)

    return tmpl_str.format(**subs)


def get_str_tc_before_event(tc: ModelBase, ns_manager: NamespaceManager) -> str:
    return get_model_rep(
        model=tc,
        tmpl_str='before event "{evt_uri}"',
        attr_mappings={URI_TIME_PRED_BEFORE_EVT: "evt_uri"},
        ns_manager=ns_manager,
    )


def get_str_tc_after_event(tc: ModelBase, ns_manager: NamespaceManager) -> str:
    return get_model_rep(
        model=tc,
        tmpl_str='after event "{evt_uri}"',
        attr_mappings={URI_TIME_PRED_AFTER_EVT: "evt_uri"},
        ns_manager=ns_manager,
    )


def get_str_tc_during_events(tc: ModelBase, ns_manager: NamespaceManager) -> str:
    return get_model_rep(
        model=tc,
        tmpl_str='from "{start_evt_uri}" until "{end_evt_uri}"',
        attr_mappings={
            URI_TIME_PRED_AFTER_EVT: "start_evt_uri",
            URI_TIME_PRED_BEFORE_EVT: "end_evt_uri",
        },
        ns_manager=ns_manager,
    )


class VariableStrTemplate:
    tmpl_str: str
    var_map: dict[URIRef, str]

    def __init__(self, tmpl_str: str, var_map: dict[URIRef, str]) -> None:
        self.tmpl_str = tmpl_str
        self.var_map = var_map

        # Ensure mappings is valid at template creation time
        try:
            _ = self.tmpl_str.format(**{m: "" for m in self.var_map.values()})
        except KeyError as e:
            raise ValueError(f"VariableStrTemplate: invalid mappings for '{self.tmpl_str}': {e}")

    def render(
        self, var_values: dict[URIRef, Any], ns_manager: Optional[NamespaceManager] = None
    ) -> str:
        subs = {}
        for uri, uri_map in self.var_map.items():
            assert uri in var_values, (
                f"VariableStrTemplate.render: no value supplied for {uri.n3(ns_manager)}"
            )
            subs[uri_map] = var_val_to_str(var_val=var_values[uri], ns_manager=ns_manager)

        return self.tmpl_str.format(**subs)


class VarTmplCreatorProtocol(Protocol):
    """Protocol for functions that create VariableStrTemplate from model objects.

    Should return None if model is invalid, e.g., wrong types.
    """

    def __call__(self, model: ModelBase, **kwargs: Any) -> Optional[VariableStrTemplate]: ...


def get_tmpl_bhv_pickplace(when_bhv: ModelBase, **kwargs) -> Optional[VariableStrTemplate]:
    if not isinstance(when_bhv, WhenBehaviourModel):
        return None

    is_pick = URI_BHV_TYPE_PICK in when_bhv.behaviour.types
    is_place = URI_BHV_TYPE_PLACE in when_bhv.behaviour.types

    if not is_pick and not is_place:
        return None

    agn_var_uri = when_bhv.get_attr(key=URI_BHV_PRED_TARGET_AGN)
    assert isinstance(agn_var_uri, URIRef), (
        f"'{when_bhv.id}' doesn't have a URI for agn attr: {agn_var_uri}"
    )
    obj_var_uri = when_bhv.get_attr(key=URI_BHV_PRED_TARGET_OBJ)
    assert isinstance(obj_var_uri, URIRef), (
        f"'{when_bhv.id}' doesn't have a URI for obj attr: {obj_var_uri}"
    )
    ws_var_uri = when_bhv.get_attr(key=URI_BHV_PRED_TARGET_WS)

    if is_place:
        assert isinstance(ws_var_uri, URIRef), (
            f"'{when_bhv.id}' doesn't have a URI for ws attr: {ws_var_uri}"
        )
        if is_pick:
            # pick and place
            return VariableStrTemplate(
                tmpl_str='"{agn}" picks "{obj}" and places it at "{ws}"',
                var_map={
                    agn_var_uri: "agn",
                    obj_var_uri: "obj",
                    ws_var_uri: "ws",
                },
            )

        # place only
        return VariableStrTemplate(
            tmpl_str='"{agn}" places "{obj}" at "{ws}"',
            var_map={
                agn_var_uri: "agn",
                obj_var_uri: "obj",
                ws_var_uri: "ws",
            },
        )

    # picks only
    return VariableStrTemplate(
        tmpl_str='"{agn}" picks "{obj}"',
        var_map={
            agn_var_uri: "agn",
            obj_var_uri: "obj",
        },
    )


def get_tmpl_fc_located_at(model: ModelBase, **kwargs) -> Optional[VariableStrTemplate]:
    if not isinstance(model, FluentClauseModel):
        return None

    if URI_BDD_TYPE_LOCATED_AT not in model.types:
        return None

    assert URI_BDD_PRED_REF_OBJ in model.variable_by_role, (
        f"LocatedAt fluent '{model.id}' does not have 'ref-obj' property"
    )
    obj_id = model.variable_by_role[URI_BDD_PRED_REF_OBJ][0]
    assert isinstance(obj_id, URIRef), (
        f"LocatedAt fluent '{model.id}' does not have URI 'ref-obj' property"
    )

    assert URI_BDD_PRED_REF_WS in model.variable_by_role, (
        f"LocatedAt fluent '{model.id}' does not have 'ref-ws' property"
    )
    ws_id = model.variable_by_role[URI_BDD_PRED_REF_WS][0]
    assert isinstance(ws_id, URIRef), (
        f"LocatedAt fluent '{model.id}' does not have URI 'ref-ws' property"
    )

    return VariableStrTemplate(
        tmpl_str='"{target_obj}" is located at "{target_ws}"',
        var_map={obj_id: "target_obj", ws_id: "target_ws"},
    )


def get_tmpl_fc_is_held(model: ModelBase, **kwargs) -> Optional[VariableStrTemplate]:
    if not isinstance(model, FluentClauseModel):
        return None

    if URI_BDD_TYPE_IS_HELD not in model.types:
        return None

    assert URI_BDD_PRED_REF_OBJ in model.variable_by_role, (
        f"IsHeldBy fluent '{model.id}' does not have 'ref-obj' property"
    )
    obj_id = model.variable_by_role[URI_BDD_PRED_REF_OBJ][0]
    assert isinstance(obj_id, URIRef), (
        f"IsHeldBy fluent '{model.id}' does not have URI 'ref-obj' property"
    )

    assert URI_BDD_PRED_REF_AGN in model.variable_by_role, (
        f"IsHeldBy fluent '{model.id}' does not have 'ref-agn' property"
    )
    agn_id = model.variable_by_role[URI_BDD_PRED_REF_AGN][0]
    assert isinstance(agn_id, URIRef), (
        f"IsHeldBy fluent '{model.id}' does not have URI 'ref-agn' property"
    )

    return VariableStrTemplate(
        tmpl_str='"{target_obj}" is held by "{agn}"', var_map={obj_id: "target_obj", agn_id: "agn"}
    )
