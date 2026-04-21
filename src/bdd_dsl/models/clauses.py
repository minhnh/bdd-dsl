# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Optional, Protocol
from rdflib import BNode, Literal, URIRef, Graph
from rdf_utils.models.common import ModelBase
from rdf_utils.collection import load_list_re
from bdd_dsl.exception import BDDConstraintViolation
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_ARG_NAMES,
    URI_BDD_PRED_ARG_VARS,
    URI_BDD_PRED_CFG_NAME,
    URI_BDD_PRED_CFG_TARGET,
    URI_BDD_PRED_CFG_VAR,
    URI_BDD_PRED_CLAUSE_OF,
    URI_BDD_PRED_REF_AGN,
    URI_BDD_PRED_REF_OBJ,
    URI_BDD_PRED_REF_WS,
    URI_BDD_PRED_TMPL_STR,
    URI_BDD_TYPE_CONFIG,
    URI_BDD_TYPE_IS_HELD,
    URI_BDD_TYPE_LOCATED_AT,
    URI_BDD_TYPE_MOVE_SAFE,
    URI_BDD_TYPE_SORTED,
    URI_BDD_TYPE_STR_TMPL,
    URI_BHV_PRED_OF_BHV,
    URI_BHV_PRED_TARGET_AGN,
    URI_BHV_PRED_TARGET_OBJ,
    URI_BHV_PRED_TARGET_WS,
    URI_BHV_TYPE_PICK,
    URI_BHV_TYPE_PLACE,
    URI_TIME_TYPE_TC,
)
from bdd_dsl.models.time_constraint import process_time_constraint_model


class IClause(object):
    clause_of: URIRef

    def __init__(self, node_id: URIRef, graph: Graph) -> None:
        clause_of_id = graph.value(subject=node_id, predicate=URI_BDD_PRED_CLAUSE_OF)
        assert isinstance(clause_of_id, URIRef), (
            f"Node '{node_id}': 'clause-of' does not link to URIRef: {clause_of_id}"
        )
        self.clause_of = clause_of_id


class FluentClauseModel(ModelBase, IClause):
    variable_by_role: dict[URIRef, list[URIRef]]  # map role URI -> ScenarioVariable URIs
    variables: set[URIRef]

    def __init__(self, graph: Graph, clause_id: URIRef, types: Optional[set[URIRef]]) -> None:
        ModelBase.__init__(self, graph=graph, node_id=clause_id, types=types)
        IClause.__init__(self, node_id=clause_id, graph=graph)

        self.variable_by_role = {}
        self.variables = set()

        assert URI_TIME_TYPE_TC in self.types, (
            f"FluentClause '{self.id}': is missing type {URI_TIME_TYPE_TC}"
        )
        process_time_constraint_model(constraint=self, graph=graph)

    def add_variables_by_role(self, graph: Graph, role_pred: URIRef):
        if role_pred not in self.variable_by_role:
            self.variable_by_role[role_pred] = []

        for var_id in graph.objects(subject=self.id, predicate=role_pred):
            assert isinstance(var_id, URIRef), (
                f"FluentClause '{self.id}': variable not a URIRef: {var_id}"
            )

            self.variable_by_role[role_pred].append(var_id)
            self.variables.add(var_id)

        assert len(self.variable_by_role[role_pred]) > 0, (
            f"clause '{self.id}' does link to a variable via '{role_pred}'"
        )


class FluentClauseLoaderProtocol(Protocol):
    """Protocol for functions that load relevant info for fluent clauses."""

    def __call__(self, graph: Graph, clause: FluentClauseModel) -> None: ...


def load_located_at_info(graph: Graph, clause: FluentClauseModel) -> None:
    clause.add_variables_by_role(graph=graph, role_pred=URI_BDD_PRED_REF_OBJ)

    clause.add_variables_by_role(graph=graph, role_pred=URI_BDD_PRED_REF_WS)
    if len(clause.variable_by_role[URI_BDD_PRED_REF_WS]) != 1:
        raise BDDConstraintViolation(
            f"FluentClasue '{clause.id}', type {clause.types},"
            f" does not refer to exactly 1 workspace: {clause.variable_by_role[URI_BDD_PRED_REF_WS]}"
        )

    return


def load_held_by_info(graph: Graph, clause: FluentClauseModel) -> None:
    clause.add_variables_by_role(graph=graph, role_pred=URI_BDD_PRED_REF_OBJ)
    clause.add_variables_by_role(graph=graph, role_pred=URI_BDD_PRED_REF_AGN)
    return


def load_move_safe_info(graph: Graph, clause: FluentClauseModel) -> None:
    clause.add_variables_by_role(graph=graph, role_pred=URI_BDD_PRED_REF_AGN)
    return


def load_sorted_info(graph: Graph, clause: FluentClauseModel) -> None:
    clause.add_variables_by_role(graph=graph, role_pred=URI_BDD_PRED_REF_OBJ)
    clause.add_variables_by_role(graph=graph, role_pred=URI_BDD_PRED_REF_WS)
    return


def load_has_config_info(graph: Graph, clause: FluentClauseModel) -> None:
    clause.add_variables_by_role(graph=graph, role_pred=URI_BDD_PRED_CFG_VAR)

    cfg_target_uri = graph.value(subject=clause.id, predicate=URI_BDD_PRED_CFG_TARGET, any=False)
    assert isinstance(cfg_target_uri, URIRef), (
        f"HasConfig Pred '{clause.id}' missing 'config-target' pred to URI: {cfg_target_uri}"
    )
    clause.set_attr(key=URI_BDD_PRED_CFG_TARGET, val=cfg_target_uri)

    cfg_name = graph.value(subject=clause.id, predicate=URI_BDD_PRED_CFG_NAME, any=False)
    assert isinstance(cfg_name, Literal), (
        f"HasConfig Pred '{clause.id}' missing 'config-name' pred to Literal: {cfg_name}"
    )
    clause.set_attr(key=URI_BDD_PRED_CFG_NAME, val=cfg_name.toPython())
    return


def get_clause_config(clause: FluentClauseModel) -> tuple[URIRef, str, URIRef]:
    cfg_target = clause.get_attr(URI_BDD_PRED_CFG_TARGET)
    assert isinstance(cfg_target, URIRef)
    cfg_var = clause.variable_by_role[URI_BDD_PRED_CFG_VAR][0]
    cfg_name = clause.get_attr(URI_BDD_PRED_CFG_NAME)
    assert isinstance(cfg_name, str)

    return (cfg_target, cfg_name, cfg_var)


def load_str_tmpl_clause(graph: Graph, clause: FluentClauseModel):
    tmpl_str_node = graph.value(subject=clause.id, predicate=URI_BDD_PRED_TMPL_STR, any=False)
    assert isinstance(tmpl_str_node, Literal), (
        f"StringTemplatePredicate '{clause.id}' missing Literal 'template-string' attr: {tmpl_str_node}"
    )
    clause.set_attr(key=URI_BDD_PRED_TMPL_STR, val=tmpl_str_node.toPython())

    arg_names_node = graph.value(subject=clause.id, predicate=URI_BDD_PRED_ARG_NAMES, any=False)
    assert isinstance(arg_names_node, BNode), (
        f"StringTemplatePredicate '{clause.id}' missing BNode 'argument-names' attr: {arg_names_node}"
    )
    arg_names = load_list_re(graph=graph, first_node=arg_names_node, parse_uri=False, quiet=False)
    clause.set_attr(key=URI_BDD_PRED_ARG_NAMES, val=arg_names)

    arg_vars_node = graph.value(subject=clause.id, predicate=URI_BDD_PRED_ARG_VARS, any=False)
    assert isinstance(arg_vars_node, BNode), (
        f"StringTemplatePredicate '{clause.id}' missing BNode 'argument-variables' attr: {arg_vars_node}"
    )
    arg_vars = load_list_re(graph=graph, first_node=arg_vars_node, parse_uri=True, quiet=False)
    for var_id in arg_vars:
        assert isinstance(var_id, URIRef), (
            f"StringTemplatePredicate '{clause.id}': not a variable IRI: {var_id}"
        )
        clause.variables.add(var_id)
    clause.set_attr(key=URI_BDD_PRED_ARG_VARS, val=arg_vars)


DEFAULT_FLUENT_LOADERS = {
    URI_BDD_TYPE_LOCATED_AT: load_located_at_info,
    URI_BDD_TYPE_IS_HELD: load_held_by_info,
    URI_BDD_TYPE_MOVE_SAFE: load_move_safe_info,
    URI_BDD_TYPE_SORTED: load_sorted_info,
    URI_BDD_TYPE_CONFIG: load_has_config_info,
    URI_BDD_TYPE_STR_TMPL: load_str_tmpl_clause,
}


class FluentClauseLoader(object):
    _loaders: dict[URIRef, FluentClauseLoaderProtocol]

    def __init__(self, loaders: dict[URIRef, FluentClauseLoaderProtocol]) -> None:
        self._loaders = loaders

    def load_clause_info(self, clause: FluentClauseModel, graph: Graph):
        processed_type = None
        for clause_type in self._loaders:
            if clause_type not in clause.types:
                continue

            processed_type = clause_type
            self._loaders[clause_type](graph=graph, clause=clause)
            break

        assert processed_type is not None, (
            f"unhandled types for fluent of clause '{clause.id}': {clause.types}"
        )


class WhenBehaviourModel(ModelBase, IClause):
    behaviour: ModelBase

    def __init__(self, clause_id: URIRef, graph: Graph) -> None:
        ModelBase.__init__(self, graph=graph, node_id=clause_id)
        IClause.__init__(self, node_id=clause_id, graph=graph)

        bhv_id = graph.value(subject=self.id, predicate=URI_BHV_PRED_OF_BHV)
        assert isinstance(bhv_id, URIRef), (
            f"WhenBehaviour '{self.id}' does not ref a behaviour URI: {bhv_id}"
        )
        self.behaviour = ModelBase(node_id=bhv_id, graph=graph)

        process_time_constraint_model(constraint=self, graph=graph)


class WhenBhvLoaderProtocol(Protocol):
    """Protocol for functions that load relevant info for WhenBehaviour."""

    def __call__(self, graph: Graph, when_bhv: WhenBehaviourModel) -> None: ...


def load_bhv_pickplace(graph: Graph, when_bhv: WhenBehaviourModel) -> None:
    assert (
        URI_BHV_TYPE_PICK in when_bhv.behaviour.types
        or URI_BHV_TYPE_PLACE in when_bhv.behaviour.types
    ), (
        f"load_bhv_pickplace: '{when_bhv.behaviour.id}' not a pick or place bhv, types: {when_bhv.behaviour.types}"
    )

    target_obj_id = graph.value(subject=when_bhv.id, predicate=URI_BHV_PRED_TARGET_OBJ)
    assert isinstance(target_obj_id, URIRef), (
        f"WhenBehaviour '{when_bhv.id}' (behaviour types: {when_bhv.behaviour.types}) does not ref target object's URI: {target_obj_id}"
    )
    when_bhv.set_attr(key=URI_BHV_PRED_TARGET_OBJ, val=target_obj_id)

    target_agn_id = graph.value(subject=when_bhv.id, predicate=URI_BHV_PRED_TARGET_AGN)
    assert isinstance(target_agn_id, URIRef), (
        f"WhenBehaviour '{when_bhv.id}' (behaviour types: {when_bhv.behaviour.types}) does not ref target agent's URI: {target_agn_id}"
    )
    when_bhv.set_attr(key=URI_BHV_PRED_TARGET_AGN, val=target_agn_id)

    if URI_BHV_TYPE_PLACE in when_bhv.behaviour.types:
        target_ws_id = graph.value(subject=when_bhv.id, predicate=URI_BHV_PRED_TARGET_WS)
        assert isinstance(target_ws_id, URIRef), (
            f"WhenBehaviour '{when_bhv.id}' (behaviour types: {when_bhv.behaviour.types}) does not ref target workspace's URI: {target_ws_id}"
        )
        when_bhv.set_attr(key=URI_BHV_PRED_TARGET_WS, val=target_ws_id)


class WhenBhvLoader(object):
    _loaders: list[WhenBhvLoaderProtocol]

    def __init__(self, loaders: list[WhenBhvLoaderProtocol]) -> None:
        self._loaders = loaders

    def load_bhv_info(self, when_bhv: WhenBehaviourModel, graph: Graph):
        for bhv_loader in self._loaders:
            bhv_loader(graph=graph, when_bhv=when_bhv)
