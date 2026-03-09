# SPDX-License-Identifier:  GPL-3.0-or-later
from numbers import Number
from typing import Any, Iterable, Optional, Protocol
from rdf_utils.models.common import ModelBase
from rdflib import URIRef
from rdflib.namespace import NamespaceManager

from bdd_dsl.models.clauses import FluentClauseModel, IClause, WhenBehaviourModel
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_CFG_NAME,
    URI_BDD_PRED_CFG_TARGET,
    URI_BDD_PRED_CFG_VAR,
    URI_BDD_PRED_REF_AGN,
    URI_BDD_PRED_REF_OBJ,
    URI_BDD_PRED_REF_WS,
    URI_BDD_TYPE_CONFIG,
    URI_BDD_TYPE_IS_HELD,
    URI_BDD_TYPE_LOCATED_AT,
    URI_BHV_PRED_TARGET_AGN,
    URI_BHV_PRED_TARGET_OBJ,
    URI_BHV_PRED_TARGET_WS,
    URI_BHV_TYPE_PICK,
    URI_BHV_TYPE_PLACE,
    URI_TIME_PRED_AFTER_EVT,
    URI_TIME_PRED_BEFORE_EVT,
    URI_TIME_TYPE_AFTER_EVT,
    URI_TIME_TYPE_BEFORE_EVT,
    URI_TIME_TYPE_DURING,
)
from bdd_dsl.models.user_story import IHasClause, ScenarioModel


def get_clause_role_rep(scenario: ScenarioModel, clause: IClause) -> str:
    if clause.clause_of == scenario.given:
        return "Given"
    if clause.clause_of == scenario.when:
        return "When"
    if clause.clause_of == scenario.then:
        return "Then"
    raise ValueError(f"Role '{clause.clause_of}' is not Given/When/Then of '{IHasClause.id}'")


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


class ModelToStrProtocol(Protocol):
    """Protocol for functions that create a string from a model object.

    Should return None if model is invalid, e.g., wrong types.
    """

    def __call__(
        self, model: ModelBase, ns_manager: Optional[NamespaceManager], **kwargs: Any
    ) -> Optional[str]: ...


def get_str_tc_before_event(
    model: ModelBase, ns_manager: Optional[NamespaceManager], **kwargs: Any
) -> Optional[str]:
    if URI_TIME_TYPE_BEFORE_EVT not in model.types:
        return None

    return get_model_rep(
        model=model,
        tmpl_str='before event "{evt_uri}"',
        attr_mappings={URI_TIME_PRED_BEFORE_EVT: "evt_uri"},
        ns_manager=ns_manager,
    )


def get_str_tc_after_event(
    model: ModelBase, ns_manager: Optional[NamespaceManager], **kwargs: Any
) -> Optional[str]:
    if URI_TIME_TYPE_AFTER_EVT not in model.types:
        return None

    return get_model_rep(
        model=model,
        tmpl_str='after event "{evt_uri}"',
        attr_mappings={URI_TIME_PRED_AFTER_EVT: "evt_uri"},
        ns_manager=ns_manager,
    )


def get_str_tc_during_events(
    model: ModelBase, ns_manager: Optional[NamespaceManager], **kwargs: Any
) -> Optional[str]:
    if URI_TIME_TYPE_DURING not in model.types:
        return None

    return get_model_rep(
        model=model,
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


class ClauseRepBuilder:
    _clause_templates: dict[URIRef, VariableStrTemplate | None]
    _clause_tmpl_creators: list[VarTmplCreatorProtocol]
    _tc_str_gens: list[ModelToStrProtocol]

    def __init__(
        self,
        tmpl_creators: list[VarTmplCreatorProtocol],
        tc_str_gens: list[ModelToStrProtocol],
    ) -> None:
        self._clause_templates = {}
        self._clause_tmpl_creators = tmpl_creators
        self._tc_str_gens = tc_str_gens

    def render_fluent_clause(
        self,
        role: str,
        clause: FluentClauseModel,
        val_dict: dict[URIRef, Any],
        ns_manager: Optional[NamespaceManager],
    ) -> str:
        clause_rep = self._render_var_clause(
            clause=clause, val_dict=val_dict, ns_manager=ns_manager
        )
        tc_rep = self._render_tc(clause=clause, ns_manager=ns_manager)
        return f"{role} {clause_rep} {tc_rep}"

    def render_when_bhv_clause(
        self,
        clause: WhenBehaviourModel,
        val_dict: dict[URIRef, Any],
        ns_manager: Optional[NamespaceManager],
    ) -> str:
        clause_rep = self._render_var_clause(
            clause=clause, val_dict=val_dict, ns_manager=ns_manager
        )
        return f"When {clause_rep}"

    def _render_var_clause(
        self,
        clause: FluentClauseModel | WhenBehaviourModel,
        val_dict: dict[URIRef, Any],
        ns_manager: Optional[NamespaceManager],
    ) -> str:
        if clause.id not in self._clause_templates:
            for tmpl_crtr in self._clause_tmpl_creators:
                tmpl = tmpl_crtr(model=clause)
                self._clause_templates[clause.id] = tmpl
                if tmpl is not None:
                    break

        tmpl = self._clause_templates[clause.id]
        if tmpl is None:
            clause_rep = clause.id.n3(ns_manager)
        else:
            clause_rep = tmpl.render(var_values=val_dict, ns_manager=ns_manager)

        return clause_rep

    def _render_tc(
        self,
        clause: FluentClauseModel | WhenBehaviourModel,
        ns_manager: Optional[NamespaceManager],
    ) -> str:

        # Render time constraint
        tc_rep = None
        for tc_gen in self._tc_str_gens:
            tc_rep = tc_gen(model=clause, ns_manager=ns_manager)
            if tc_rep is not None:
                break
        if tc_rep is None:
            tc_rep = f"(no TimeConstraint rep for '{clause.id.n3(ns_manager)}')"

        return tc_rep


def get_tmpl_bhv_pickplace(model: ModelBase, **kwargs) -> Optional[VariableStrTemplate]:
    if not isinstance(model, WhenBehaviourModel):
        return None

    is_pick = URI_BHV_TYPE_PICK in model.behaviour.types
    is_place = URI_BHV_TYPE_PLACE in model.behaviour.types

    if not is_pick and not is_place:
        return None

    agn_var_uri = model.get_attr(key=URI_BHV_PRED_TARGET_AGN)
    assert isinstance(agn_var_uri, URIRef), (
        f"'{model.id}' doesn't have a URI for agn attr: {agn_var_uri}"
    )
    obj_var_uri = model.get_attr(key=URI_BHV_PRED_TARGET_OBJ)
    assert isinstance(obj_var_uri, URIRef), (
        f"'{model.id}' doesn't have a URI for obj attr: {obj_var_uri}"
    )
    ws_var_uri = model.get_attr(key=URI_BHV_PRED_TARGET_WS)

    if is_place:
        assert isinstance(ws_var_uri, URIRef), (
            f"'{model.id}' doesn't have a URI for ws attr: {ws_var_uri}"
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


def get_tmpl_fc_config(model: ModelBase, **kwargs) -> Optional[VariableStrTemplate]:
    if not isinstance(model, FluentClauseModel):
        return None

    if URI_BDD_TYPE_CONFIG not in model.types:
        return None

    ns_manager = kwargs.get("ns_manager", None)

    assert URI_BDD_PRED_CFG_VAR in model.variable_by_role, (
        f"HasConfig fluent '{model.id}' does not have 'config-var' property"
    )
    cfg_var_id = model.variable_by_role[URI_BDD_PRED_CFG_VAR][0]
    assert isinstance(cfg_var_id, URIRef), (
        f"HasConfig fluent '{model.id}' does not have URI 'config-var' property"
    )

    cfg_name = model.get_attr(URI_BDD_PRED_CFG_NAME)
    target_uri = model.get_attr(URI_BDD_PRED_CFG_TARGET)
    assert isinstance(target_uri, URIRef)

    return VariableStrTemplate(
        tmpl_str=f'"{target_uri.n3(ns_manager)}" has config "{cfg_name}" = "{{cfg_val}}"',
        var_map={cfg_var_id: "cfg_val"},
    )
