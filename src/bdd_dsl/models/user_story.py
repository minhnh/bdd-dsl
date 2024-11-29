# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Any, Callable, Generator, Iterable, Optional
from rdflib import RDF, Graph, URIRef, BNode
from rdflib.namespace import NamespaceManager
from rdflib.query import ResultRow
from rdf_utils.naming import get_valid_var_name
from rdf_utils.models.common import ModelBase, get_node_types
from rdf_utils.collection import load_list_re
from rdf_utils.uri import URL_MM_PYTHON_SHACL, URL_SECORO_MM
from rdf_utils.constraints import check_shacl_constraints
from bdd_dsl.exception import BDDConstraintViolation
from bdd_dsl.models.agent import AgentModel, AgnModelLoader
from bdd_dsl.models.combinatorics import SetEnumerationModel
from bdd_dsl.models.environment import ObjModelLoader, ObjectModel
from bdd_dsl.models.namespace import NS_MANAGER
from bdd_dsl.models.queries import Q_USER_STORY
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_CLAUSE_OF,
    URI_BDD_PRED_GIVEN,
    URI_BDD_PRED_HAS_CLAUSE,
    URI_BDD_PRED_HAS_VARIATION,
    URI_BDD_PRED_HOLDS,
    URI_BDD_PRED_HOLDS_AT,
    URI_BDD_PRED_OF_SETS,
    URI_BDD_PRED_REF_AGN,
    URI_BDD_PRED_REF_OBJ,
    URI_BDD_PRED_REF_WS,
    URI_BDD_PRED_ROWS,
    URI_BDD_PRED_THEN,
    URI_BDD_PRED_VAR_LIST,
    URI_BDD_PRED_WHEN,
    URI_BDD_TYPE_CART_PRODUCT,
    URI_BDD_TYPE_EXISTS,
    URI_BDD_TYPE_FLUENT_CLAUSE,
    URI_BDD_TYPE_FORALL,
    URI_BDD_TYPE_IS_HELD,
    URI_BDD_TYPE_LOCATED_AT,
    URI_BDD_TYPE_SCENARIO,
    URI_BDD_TYPE_SCENE_AGN,
    URI_BDD_TYPE_SCENE_OBJ,
    URI_BDD_PRED_HAS_SCENE,
    URI_BDD_PRED_OF_SCENARIO,
    URI_BDD_PRED_OF_TMPL,
    URI_BDD_PRED_HAS_AC,
    URI_BDD_TYPE_SCENE_WS,
    URI_BDD_TYPE_TABLE_VAR,
    URI_BDD_TYPE_US,
    URI_BHV_PRED_OF_BHV,
    URI_TASK_PRED_OF_TASK,
    URI_ENV_PRED_HAS_OBJ,
    URI_ENV_PRED_HAS_WS,
    URI_AGN_PRED_HAS_AGN,
    URI_TIME_PRED_REF_EVT,
    URI_TIME_TYPE_AFTER_EVT,
    URI_TIME_TYPE_BEFORE_EVT,
)


BDD_SHACL_URLS = {
    f"{URL_SECORO_MM}/acceptance-criteria/bdd/bdd.shacl.ttl": "turtle",
    f"{URL_SECORO_MM}/acceptance-criteria/bdd/time.shacl.ttl": "turtle",
    f"{URL_SECORO_MM}/acceptance-criteria/bdd/environment.shacl.ttl": "turtle",
    f"{URL_SECORO_MM}/acceptance-criteria/bdd/agent.shacl.ttl": "turtle",
    f"{URL_SECORO_MM}/acceptance-criteria/bdd/simulation.shacl.ttl": "turtle",
    URL_MM_PYTHON_SHACL: "turtle",
}
Q_US_VAR = f"""
SELECT DISTINCT ?us ?var WHERE {{
    ?us a {URI_BDD_TYPE_US.n3()} .
    ?us {URI_BDD_PRED_HAS_AC.n3()} ?var .
}}
"""


class TimeConstraintModel(ModelBase):
    def __init__(self, full_graph: Graph, tc_id: URIRef) -> None:
        super().__init__(graph=full_graph, node_id=tc_id)


def process_time_constraint_model(constraint: TimeConstraintModel, full_graph: Graph):
    if URI_TIME_TYPE_BEFORE_EVT in constraint.types or URI_TIME_TYPE_AFTER_EVT in constraint.types:
        event_ids = list(full_graph.objects(subject=constraint.id, predicate=URI_TIME_PRED_REF_EVT))
        if len(event_ids) != 1:
            raise BDDConstraintViolation(
                f"TimeConstraint '{constraint.id}' of  type '{constraint.types}'"
                f" does not refer to exactly 1 event: {event_ids}"
            )
        assert isinstance(event_ids[0], URIRef), f"event ref not a URIRef: {event_ids[0]}"
        assert not constraint.has_attr(
            key=URI_TIME_PRED_REF_EVT
        ), f"contraint '{constraint.id}' doesn't have :ref-event attribute"
        constraint.set_attr(key=URI_TIME_PRED_REF_EVT, val=event_ids[0])


class ScenarioModel(ModelBase):
    given: URIRef
    when: URIRef
    then: URIRef
    bhv_id: URIRef
    task_id: URIRef

    def __init__(self, scenario_id: URIRef, graph: Graph) -> None:
        super().__init__(node_id=scenario_id, types={URI_BDD_TYPE_SCENARIO})

        node_val = graph.value(subject=self.id, predicate=URI_BDD_PRED_GIVEN)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"Scenario '{self.id}' does not refer to a Given"
        self.given = node_val

        node_val = graph.value(subject=self.id, predicate=URI_BDD_PRED_WHEN)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"Scenario '{self.id}' does not refer to a When"
        self.when = node_val

        node_val = graph.value(subject=self.id, predicate=URI_BDD_PRED_THEN)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"Scenario '{self.id}' does not refer to a Then"
        self.then = node_val

        node_val = graph.value(subject=self.id, predicate=URI_BHV_PRED_OF_BHV)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"Scenario '{self.id}' does not refer to a Behaviour"
        self.bhv_id = node_val

        node_val = graph.value(subject=self.id, predicate=URI_TASK_PRED_OF_TASK)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"Scenario '{self.id}' does not refer to a Task"
        self.task_id = node_val


class IClause(object):
    clause_of: URIRef

    def __init__(self, node_id: URIRef, graph: Graph) -> None:
        clause_of_id = graph.value(subject=node_id, predicate=URI_BDD_PRED_CLAUSE_OF)
        assert isinstance(
            clause_of_id, URIRef
        ), f"Node '{node_id}': 'clause-of' does not link to URIRef: {clause_of_id}"
        self.clause_of = clause_of_id


class IHasClause(ModelBase):
    _clauses: dict[URIRef, ModelBase]
    _clauses_by_role: dict[URIRef, set[URIRef]]  # given/when/then URI -> clause URI
    variables: set[URIRef]
    scenario: ScenarioModel

    def __init__(
        self,
        node_id: URIRef,
        scenario: ScenarioModel,
        graph: Optional[Graph] = None,
        types: Optional[set[URIRef]] = None,
    ) -> None:
        super().__init__(node_id=node_id, graph=graph, types=types)
        self.variables = set()
        self.scenario = scenario
        self._clauses = {}
        self._clauses_by_role = {scenario.given: set(), scenario.when: set(), scenario.then: set()}

    def _process_iclause(self, clause: IClause):
        assert isinstance(
            clause, ModelBase
        ), f"{self.id}: got IClause which is not also a ModelBase: {clause}"
        assert (
            clause.clause_of in self._clauses_by_role
        ), f"{self.id}: IClause '{clause.id}' does not ref Given, When, Then of parent scenario '{self.scenario.id}'"

        assert clause.id not in self._clauses, f"{self.id}: duplicate clause: {clause.id}"
        self._clauses[clause.id] = clause
        self._clauses_by_role[clause.clause_of].add(clause.id)

    def _load_clauses_re(self, node_id: URIRef, graph: Graph, has_clause_set: set[URIRef]) -> None:
        if node_id in has_clause_set:
            raise RuntimeError(f"load_clause_re: loop detected at node '{node_id}'")
        has_clause_set.add(node_id)

        has_clause_obj = graph.value(subject=node_id, predicate=URI_BDD_PRED_HAS_CLAUSE)
        if has_clause_obj is None:
            # no has-clause
            return
        assert isinstance(
            has_clause_obj, BNode
        ), f"'{node_id}': 'has-clause' does not refer to BNode: {has_clause_obj}"

        for clause_id in graph.items(list=has_clause_obj):
            assert isinstance(
                clause_id, URIRef
            ), f"'{node_id}': item in 'has-clause' collection not a URIRef: {clause_id}"
            assert clause_id not in self._clauses, f"'{node_id}': duplicate clause '{clause_id}'"

            clause_types = get_node_types(graph=graph, node_id=clause_id)
            if URI_BDD_TYPE_FLUENT_CLAUSE in clause_types:
                clause = FluentClauseModel(
                    full_graph=graph, clause_id=clause_id, types=clause_types
                )
                self._process_iclause(clause=clause)
                for var_id in clause.role_by_variable.keys():
                    self.variables.add(var_id)
                continue

            if URI_BDD_TYPE_FORALL in clause_types:
                forall_model = ForAllModel(
                    forall_id=clause_id,
                    scenario=self.scenario,
                    graph=graph,
                    types=clause_types,
                )
                self._process_iclause(clause=forall_model)
                forall_model._load_clauses_re(
                    node_id=forall_model.id, graph=graph, has_clause_set=has_clause_set
                )
                continue

            if URI_BDD_TYPE_EXISTS in clause_types:
                exists_model = ThereExistsModel(
                    exists_id=clause_id,
                    scenario=self.scenario,
                    graph=graph,
                    types=clause_types,
                )
                self._process_iclause(clause=exists_model)
                exists_model._load_clauses_re(
                    node_id=exists_model.id, graph=graph, has_clause_set=has_clause_set
                )
                continue

            raise RuntimeError(f"Clause '{clause_id}' has unexpected types: {clause_types}")


class ForAllModel(IHasClause, IClause):
    def __init__(
        self,
        forall_id: URIRef,
        scenario: ScenarioModel,
        graph: Graph,
        types: Optional[set[URIRef]] = None,
    ) -> None:
        IHasClause.__init__(self, node_id=forall_id, scenario=scenario, graph=graph, types=types)
        IClause.__init__(self, node_id=forall_id, graph=graph)


class ThereExistsModel(IHasClause, IClause):
    clause_of: URIRef

    def __init__(
        self,
        exists_id: URIRef,
        scenario: ScenarioModel,
        graph: Graph,
        types: Optional[set[URIRef]] = None,
    ) -> None:
        IHasClause.__init__(self, node_id=exists_id, scenario=scenario, graph=graph, types=types)
        IClause.__init__(self, node_id=exists_id, graph=graph)


class FluentClauseModel(ModelBase, IClause):
    fluent: ModelBase
    time_constraint: TimeConstraintModel
    variable_by_role: dict[URIRef, list[URIRef]]  # map role URI -> ScenarioVariable URIs
    role_by_variable: dict[URIRef, list[URIRef]]  # map ScenarioVariable URI -> role URIs

    def __init__(self, full_graph: Graph, clause_id: URIRef, types: Optional[set[URIRef]]) -> None:
        ModelBase.__init__(self, graph=full_graph, node_id=clause_id, types=types)
        IClause.__init__(self, node_id=clause_id, graph=full_graph)

        fluent_id = full_graph.value(subject=clause_id, predicate=URI_BDD_PRED_HOLDS)
        assert isinstance(
            fluent_id, URIRef
        ), f"FluentClause '{self.id}': holds doesn't link to URIRef: {fluent_id}"
        self.fluent = ModelBase(graph=full_graph, node_id=fluent_id)

        self.variable_by_role = {}
        self.role_by_variable = {}
        self.process_builtin_fluent_types(full_graph=full_graph)

        tc_id = full_graph.value(subject=clause_id, predicate=URI_BDD_PRED_HOLDS_AT)
        assert isinstance(
            tc_id, URIRef
        ), f"FluentClause '{self.id}': holds-at doesn't link to URIRef"
        tc = TimeConstraintModel(full_graph=full_graph, tc_id=tc_id)
        process_time_constraint_model(constraint=tc, full_graph=full_graph)
        self.time_constraint = tc

    def add_variables_by_role(self, full_graph: Graph, role_pred: URIRef):
        if role_pred not in self.variable_by_role:
            self.variable_by_role[role_pred] = []

        for var_id in full_graph.objects(subject=self.id, predicate=role_pred):
            assert isinstance(
                var_id, URIRef
            ), f"FluentClause '{self.id}': variable not a URIRef: {var_id}"

            self.variable_by_role[role_pred].append(var_id)

            if var_id not in self.role_by_variable:
                self.role_by_variable[var_id] = []
            self.role_by_variable[var_id].append(var_id)

        assert (
            len(self.variable_by_role[role_pred]) > 0
        ), f"clause '{self.id}' does link to a variable via '{role_pred}'"

    def process_builtin_fluent_types(self, full_graph: Graph):
        if URI_BDD_TYPE_LOCATED_AT in self.fluent.types:
            self.add_variables_by_role(full_graph=full_graph, role_pred=URI_BDD_PRED_REF_OBJ)
            if len(self.variable_by_role[URI_BDD_PRED_REF_OBJ]) != 1:
                raise BDDConstraintViolation(
                    f"Fluent '{self.fluent.id}' of clause '{self.id}', type 'LocatedAt',"
                    f" does not refer to exactly 1 object: {self.variable_by_role[URI_BDD_PRED_REF_OBJ]}"
                )

            self.add_variables_by_role(full_graph=full_graph, role_pred=URI_BDD_PRED_REF_WS)
            if len(self.variable_by_role[URI_BDD_PRED_REF_WS]) != 1:
                raise BDDConstraintViolation(
                    f"Fluent '{self.fluent.id}' of clause '{self.id}', type 'LocatedAt',"
                    f" does not refer to exactly 1 workspace: {self.variable_by_role[URI_BDD_PRED_REF_WS]}"
                )

            return

        if URI_BDD_TYPE_IS_HELD in self.fluent.types:
            self.add_variables_by_role(full_graph=full_graph, role_pred=URI_BDD_PRED_REF_OBJ)
            if len(self.variable_by_role[URI_BDD_PRED_REF_OBJ]) != 1:
                raise BDDConstraintViolation(
                    f"Fluent '{self.fluent.id}' of clause '{self.id}', type 'IsHeld',"
                    f" does not refer to exactly 1 object: {self.variable_by_role[URI_BDD_PRED_REF_OBJ]}"
                )

            self.add_variables_by_role(full_graph=full_graph, role_pred=URI_BDD_PRED_REF_AGN)
            if len(self.variable_by_role[URI_BDD_PRED_REF_AGN]) != 1:
                raise BDDConstraintViolation(
                    f"Fluent '{self.fluent.id}' of clause '{self.id}', type 'IsHeld',"
                    f" does not refer to exactly 1 agent: {self.variable_by_role[URI_BDD_PRED_REF_AGN]}"
                )

            return

        raise RuntimeError(
            f"process_builtin_fluent_types: unhandled types for fluent '{self.fluent.id}' of clause '{self.id}':"
            f" {self.fluent.types}"
        )


def get_time_constraint_str(
    tc_model: TimeConstraintModel, ns_manager: NamespaceManager = NS_MANAGER
) -> str:
    if URI_TIME_TYPE_BEFORE_EVT in tc_model.types or URI_TIME_TYPE_AFTER_EVT in tc_model.types:
        evt_uri = tc_model.get_attr(key=URI_TIME_PRED_REF_EVT)
        assert (
            evt_uri is not None
        ), f"TimeConstraint '{tc_model.id}' of types '{tc_model.types}' does ref an event or event attr not loaded"
        assert isinstance(
            evt_uri, URIRef
        ), f"unexpected type for event URI '{evt_uri}': {type(evt_uri)}"
        evt_uri_str = evt_uri.n3(ns_manager)

        if URI_TIME_TYPE_BEFORE_EVT in tc_model.types:
            return f'before event "{evt_uri_str}"'

        if URI_TIME_TYPE_AFTER_EVT in tc_model.types:
            return f'after event "{evt_uri_str}"'

    raise RuntimeError(f"TimeConstraint '{tc_model.id}' has unhandled types: {tc_model.types}")


def get_clause_str(
    clause: FluentClauseModel,
    ns_manager: NamespaceManager = NS_MANAGER,
    tc_str_func: Callable[[TimeConstraintModel, NamespaceManager], str] = get_time_constraint_str,
) -> str:
    if URI_BDD_TYPE_LOCATED_AT in clause.fluent.types:
        assert URI_BDD_PRED_REF_OBJ in clause.variable_by_role
        obj_id = clause.variable_by_role[URI_BDD_PRED_REF_OBJ][0]
        assert isinstance(obj_id, URIRef)
        obj_id_str = get_valid_var_name(obj_id.n3(ns_manager))

        assert URI_BDD_PRED_REF_WS in clause.variable_by_role
        ws_id = clause.variable_by_role[URI_BDD_PRED_REF_WS][0]
        assert isinstance(ws_id, URIRef)
        ws_id_str = get_valid_var_name(ws_id.n3(ns_manager))

        return f'"<{obj_id_str}>" is located at "<{ws_id_str}>" {tc_str_func(clause.time_constraint, ns_manager)}'

    if URI_BDD_TYPE_IS_HELD in clause.fluent.types:
        assert URI_BDD_PRED_REF_OBJ in clause.variable_by_role
        obj_id = clause.variable_by_role[URI_BDD_PRED_REF_OBJ][0]
        assert isinstance(obj_id, URIRef)
        obj_id_str = get_valid_var_name(obj_id.n3(ns_manager))

        assert URI_BDD_PRED_REF_AGN in clause.variable_by_role
        agn_id = clause.variable_by_role[URI_BDD_PRED_REF_AGN][0]
        assert isinstance(agn_id, URIRef)
        agn_id_str = get_valid_var_name(agn_id.n3(ns_manager))

        return f'"<{obj_id_str}>" is held by "<{agn_id_str}>" {tc_str_func(clause.time_constraint, ns_manager)}'

    raise RuntimeError(
        f"get_clause_str: unhandled types for fluent '{clause.fluent.id}' of clasue '{clause.id}':"
        f" {clause.fluent.types}"
    )


class SceneModel(ModelBase):
    """Assuming the given graph is constructed as a query result from `URL_Q_BDD_US`"""

    objects: set[URIRef]  # object URIs
    workspaces: dict[URIRef, set]  # workspace URI -> ws types
    agents: set[URIRef]  # agent URIs
    obj_model_loader: ObjModelLoader
    agn_model_loader: AgnModelLoader

    def __init__(self, us_graph: Graph, full_graph: Graph, scene_id: URIRef) -> None:
        super().__init__(graph=full_graph, node_id=scene_id)
        self.objects = set()
        self.workspaces = {}
        self.agents = set()
        self.obj_model_loader = ObjModelLoader()
        self.agn_model_loader = AgnModelLoader()

        for comp_id in us_graph.objects(subject=scene_id, predicate=URI_BDD_PRED_HAS_SCENE):
            comp_types = set(us_graph.objects(subject=comp_id, predicate=RDF.type))
            assert len(comp_types) > 0, f"composition '{comp_id}' of scene '{scene_id}' has no type"

            if URI_BDD_TYPE_SCENE_OBJ in comp_types:
                for obj_id in full_graph.objects(subject=comp_id, predicate=URI_ENV_PRED_HAS_OBJ):
                    assert isinstance(
                        obj_id, URIRef
                    ), f"SceneModel {self.id}: '{obj_id}' not URIRef"
                    self.objects.add(obj_id)

            if URI_BDD_TYPE_SCENE_WS in comp_types:
                for ws_id in full_graph.objects(subject=comp_id, predicate=URI_ENV_PRED_HAS_WS):
                    assert isinstance(ws_id, URIRef)
                    ws_types = set(full_graph.objects(subject=ws_id, predicate=RDF.type))
                    self.workspaces[ws_id] = ws_types

            if URI_BDD_TYPE_SCENE_AGN in comp_types:
                for agn_id in full_graph.objects(subject=comp_id, predicate=URI_AGN_PRED_HAS_AGN):
                    assert isinstance(agn_id, URIRef)
                    self.agents.add(agn_id)

    def load_obj_model(
        self, graph: Graph, obj_id: URIRef, override: bool = False, **kwargs: Any
    ) -> ObjectModel:
        assert obj_id in self.objects, f"Object '{obj_id}' not in scene"
        return self.obj_model_loader.load_object_model(
            graph=graph, obj_id=obj_id, override=override, **kwargs
        )

    def load_agn_model(
        self, graph: Graph, agent_id: URIRef, override: bool = False, **kwargs: Any
    ) -> AgentModel:
        assert agent_id in self.agents, f"Agent '{agent_id}' not in scene"
        return self.agn_model_loader.load_agent_model(
            graph=graph, agent_id=agent_id, override=override, **kwargs
        )


class TaskVariationModel(ModelBase):
    task_id: URIRef
    variables: set[URIRef]
    set_enums: dict[URIRef, SetEnumerationModel]

    def __init__(self, us_graph: Graph, full_graph: Graph, task_var_id: URIRef) -> None:
        super().__init__(graph=us_graph, node_id=task_var_id)
        task_id = us_graph.value(subject=task_var_id, predicate=URI_TASK_PRED_OF_TASK)
        assert isinstance(task_id, URIRef), f"task_id is not URIRef: type={type(task_id)}"
        self.task_id = task_id
        self.variables = set()
        self.set_enums = {}

        self._process_builtin_task_var_types(full_graph)

    def _process_builtin_task_var_types(self, full_graph: Graph) -> None:
        if URI_BDD_TYPE_CART_PRODUCT in self.types:
            var_list = self._get_variable_list(graph=full_graph)

            of_sets_list_node = full_graph.value(subject=self.id, predicate=URI_BDD_PRED_OF_SETS)
            assert isinstance(
                of_sets_list_node, BNode
            ), f"CartesianProductVariation '{self.id}' does not have a valid 'of-sets' property: {of_sets_list_node}"

            sets_list = load_list_re(
                graph=full_graph, first_node=of_sets_list_node, parse_uri=True, quiet=True
            )

            assert (
                len(sets_list) == len(var_list)
            ), f"length mismatch 'variable-list' (len={len(var_list)}) != 'of-sets' (len={len(sets_list)})"

            for sets_data in sets_list:
                if isinstance(sets_data, list):
                    continue

                if not isinstance(sets_data, URIRef):
                    raise RuntimeError(
                        f"TaskVariation '{self.id}': unexpected sets type for: {sets_data}"
                    )

                if sets_data in self.set_enums:
                    continue

                # parse as SetEnumerationModel
                self.set_enums[sets_data] = SetEnumerationModel(node_id=sets_data, graph=full_graph)

            self.set_attr(key=URI_BDD_PRED_VAR_LIST, val=var_list)
            self.set_attr(key=URI_BDD_PRED_OF_SETS, val=sets_list)

            return

        if URI_BDD_TYPE_TABLE_VAR in self.types:
            var_list = self._get_variable_list(graph=full_graph)
            rows_head = full_graph.value(subject=self.id, predicate=URI_BDD_PRED_ROWS)
            assert isinstance(
                rows_head, BNode
            ), f"TableVariation '{self.id}' does not have valid 'rows' property: {rows_head}"

            rows = load_list_re(graph=full_graph, first_node=rows_head, parse_uri=True, quiet=True)
            for row in rows:
                assert len(row) == len(
                    var_list
                ), f"TableVariation '{self.id}': row length does not match variable list: {row}"
            self.set_attr(key=URI_BDD_PRED_VAR_LIST, val=var_list)
            self.set_attr(key=URI_BDD_PRED_ROWS, val=rows)

            return

        raise RuntimeError(f"TaskVariation '{self.id}' has unhandled types: {self.types}")

    def _get_variable_list(self, graph: Graph) -> list[URIRef]:
        var_list_first_node = graph.value(subject=self.id, predicate=URI_BDD_PRED_VAR_LIST)
        assert (
            var_list_first_node is not None
        ), f"TaskVariation '{self.id}' does not have 'variable-list' property"

        var_list = []
        for var_id in graph.items(list=var_list_first_node):
            assert isinstance(var_id, URIRef)
            self.variables.add(var_id)
            var_list.append(var_id)

        return var_list


class ScenarioVariantModel(IHasClause):
    """Assuming the given graph is constructed as a query result from `URL_Q_BDD_US`"""

    us_id: URIRef
    tmpl_id: URIRef
    scene: SceneModel
    task_variation: TaskVariationModel

    def __init__(self, us_graph: Graph, full_graph: Graph, var_id: URIRef) -> None:
        node_val = us_graph.value(subject=var_id, predicate=URI_BDD_PRED_OF_SCENARIO)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"ScenarioVariant '{var_id}' does not refer to a Scenario"
        scenario_id = node_val

        scenario = ScenarioModel(scenario_id=scenario_id, graph=us_graph)
        super().__init__(node_id=var_id, scenario=scenario, graph=us_graph)

        node_val = us_graph.value(subject=var_id, predicate=URI_BDD_PRED_OF_TMPL)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"ScenarioVariant '{var_id}' does not refer to a ScenarioTemplate"
        self.tmpl_id = node_val

        scene_id = us_graph.value(subject=var_id, predicate=URI_BDD_PRED_HAS_SCENE)
        assert scene_id is not None and isinstance(
            scene_id, URIRef
        ), f"ScenarioVariant '{var_id}' does not refer to a Scene"
        self.scene = SceneModel(us_graph=us_graph, full_graph=full_graph, scene_id=scene_id)

        us_ids = list(us_graph.subjects(object=var_id, predicate=URI_BDD_PRED_HAS_AC))
        assert len(us_ids) == 1 and isinstance(
            us_ids[0], URIRef
        ), f"ScenarioVariant 'var_id' is not referred from exactly 1 UserStory, found: {us_ids}"
        self.us_id = us_ids[0]

        self._tmpl_clauses = set()
        self._variant_clauses = set()

        clause_set = set()
        self._load_clauses_re(node_id=self.tmpl_id, graph=full_graph, has_clause_set=clause_set)
        self._load_clauses_re(node_id=self.id, graph=full_graph, has_clause_set=clause_set)

        task_var_id = us_graph.value(subject=var_id, predicate=URI_BDD_PRED_HAS_VARIATION)
        assert task_var_id is not None and isinstance(
            task_var_id, URIRef
        ), f"ScenarioVariant '{var_id}' does not refer to a TaskVariation"
        self.task_variation = TaskVariationModel(
            us_graph=us_graph, full_graph=full_graph, task_var_id=task_var_id
        )

    def get_given_clause_models(self) -> Generator[ModelBase, None, None]:
        for given_clause_id in self._clauses_by_role[self.scenario.given]:
            yield self._clauses[given_clause_id]

    def get_then_clause_models(self) -> Generator[ModelBase, None, None]:
        for then_clause_id in self._clauses_by_role[self.scenario.then]:
            yield self._clauses[then_clause_id]


class UserStoryLoader(object):
    def __init__(self, graph: Graph, shacl_check=True, quiet=False) -> None:
        if shacl_check:
            check_shacl_constraints(graph=graph, shacl_dict=BDD_SHACL_URLS, quiet=quiet)

        q_result = graph.query(Q_USER_STORY)
        assert (
            q_result.type == "CONSTRUCT" and q_result.graph is not None and len(q_result.graph) > 0
        ), "Model graph does not match 'bdd.models.queries.Q_USER_STORY' query"
        self._us_graph = q_result.graph

        # add namespaces from given graph to ensure consistent parsing of short URIs
        for prefix, uri in graph.namespaces():
            self._us_graph.bind(prefix=prefix, namespace=uri, override=True)

        self._scenario_variants = {}

    def load_scenario_variant(self, full_graph: Graph, variant_id: URIRef) -> ScenarioVariantModel:
        if variant_id in self._scenario_variants:
            return self._scenario_variants[variant_id]

        var_model = ScenarioVariantModel(
            us_graph=self._us_graph, full_graph=full_graph, var_id=variant_id
        )
        self._scenario_variants[variant_id] = var_model
        return var_model

    def get_us_scenario_variants(self) -> dict[URIRef, set[URIRef]]:
        """
        returns { <UserStory URI> : [ <list of ScenarioVariant URIs> ] }
        """
        q_result = self._us_graph.query(Q_US_VAR)
        assert q_result is not None, "querying scenario variant returns None query"
        assert q_result.type == "SELECT" and isinstance(
            q_result, Iterable
        ), f"unexpected query result: type={q_result.type}"

        us_var_dict = {}
        for row in q_result:
            assert isinstance(row, ResultRow), f"unexpected type for result row: {type(row)}"
            assert hasattr(row, "us"), "query result row has no attribute 'us'"
            assert hasattr(row, "var"), "query result row has no attribute 'var'"

            us_id = row.us
            assert isinstance(
                us_id, URIRef
            ), f"query result for UserStory is not a URIRef: {type(us_id)}"
            var_id = row.var
            assert isinstance(
                var_id, URIRef
            ), f"query result for ScenarioVariant is not a URIRef: {type(var_id)}"

            if us_id not in us_var_dict:
                us_var_dict[us_id] = set()

            us_var_dict[us_id].add(var_id)

        return us_var_dict
