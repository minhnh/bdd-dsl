# SPDX-License-Identifier:  GPL-3.0-or-later
from itertools import combinations
from typing import Any, Dict, Generator, Iterable
from rdflib import RDF, Graph, Literal, URIRef
from rdflib.namespace import NamespaceManager
from rdflib.query import ResultRow
from rdf_utils.naming import get_valid_var_name
from rdf_utils.uri import URL_MM_PYTHON_SHACL, URL_SECORO_MM
from rdf_utils.constraints import check_shacl_constraints
from bdd_dsl.exception import BDDConstraintViolation
from bdd_dsl.models.common import ModelBase
from bdd_dsl.models.namespace import NS_MANAGER
from bdd_dsl.models.queries import Q_USER_STORY
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_CLAUSE_OF,
    URI_BDD_PRED_FROM,
    URI_BDD_PRED_GIVEN,
    URI_BDD_PRED_HAS_CLAUSE,
    URI_BDD_PRED_HAS_VARIATION,
    URI_BDD_PRED_HOLDS,
    URI_BDD_PRED_HOLDS_AT,
    URI_BDD_PRED_OF_SETS,
    URI_BDD_PRED_REF_AGN,
    URI_BDD_PRED_REF_OBJ,
    URI_BDD_PRED_REF_WS,
    URI_BDD_PRED_REP_ALLOWED,
    URI_BDD_PRED_ROWS,
    URI_BDD_PRED_SELECT,
    URI_BDD_PRED_THEN,
    URI_BDD_PRED_VAR_LIST,
    URI_BDD_PRED_WHEN,
    URI_BDD_TYPE_CART_PRODUCT,
    URI_BDD_TYPE_COMBINATION,
    URI_BDD_TYPE_IS_HELD,
    URI_BDD_TYPE_LOCATED_AT,
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
KEY_EVT_ID = "event_id"


class TimeConstraintModel(ModelBase):
    attributes: dict

    def __init__(self, full_graph: Graph, tc_id: URIRef) -> None:
        super().__init__(graph=full_graph, node_id=tc_id)
        self.attributes = {}


def process_time_constraint_model(constraint: TimeConstraintModel, full_graph: Graph):
    if URI_TIME_TYPE_BEFORE_EVT in constraint.types or URI_TIME_TYPE_AFTER_EVT in constraint.types:
        event_ids = list(full_graph.objects(subject=constraint.id, predicate=URI_TIME_PRED_REF_EVT))
        if len(event_ids) != 1:
            raise BDDConstraintViolation(
                f"TimeConstraint '{constraint.id}' of  type '{constraint.types}'"
                f" does not refer to exactly 1 event: {event_ids}"
            )
        assert isinstance(event_ids[0], URIRef)
        assert KEY_EVT_ID not in constraint.attributes
        constraint.attributes[KEY_EVT_ID] = event_ids[0]


class FluentClauseModel(ModelBase):
    clause_of: URIRef
    fluent: ModelBase
    time_constraint: TimeConstraintModel
    variable_by_role: Dict[URIRef, list[URIRef]]  # map role URI -> ScenarioVariable URIs
    role_by_variable: Dict[URIRef, list[URIRef]]  # map ScenarioVariable URI -> role URIs

    def __init__(self, full_graph: Graph, clause_id: URIRef) -> None:
        super().__init__(graph=full_graph, node_id=clause_id)

        clause_of_id = full_graph.value(subject=clause_id, predicate=URI_BDD_PRED_CLAUSE_OF)
        assert isinstance(clause_of_id, URIRef)
        self.clause_of = clause_of_id

        fluent_id = full_graph.value(subject=clause_id, predicate=URI_BDD_PRED_HOLDS)
        assert isinstance(fluent_id, URIRef)
        self.fluent = ModelBase(graph=full_graph, node_id=fluent_id)

        self.variable_by_role = {}
        self.role_by_variable = {}
        self.process_builtin_fluent_types(full_graph=full_graph)

        tc_id = full_graph.value(subject=clause_id, predicate=URI_BDD_PRED_HOLDS_AT)
        assert isinstance(tc_id, URIRef)
        tc = TimeConstraintModel(full_graph=full_graph, tc_id=tc_id)
        process_time_constraint_model(constraint=tc, full_graph=full_graph)
        self.time_constraint = tc

    def add_variables_by_role(self, full_graph: Graph, role_pred: URIRef):
        if role_pred not in self.variable_by_role:
            self.variable_by_role[role_pred] = []

        for var_id in full_graph.objects(subject=self.id, predicate=role_pred):
            assert isinstance(var_id, URIRef)

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


def get_clause_str(clause: FluentClauseModel, ns_manager: NamespaceManager = NS_MANAGER) -> str:
    if URI_BDD_TYPE_LOCATED_AT in clause.fluent.types:
        assert URI_BDD_PRED_REF_OBJ in clause.variable_by_role
        obj_id = clause.variable_by_role[URI_BDD_PRED_REF_OBJ][0]
        assert isinstance(obj_id, URIRef)
        obj_id_str = get_valid_var_name(obj_id.n3(ns_manager))

        assert URI_BDD_PRED_REF_WS in clause.variable_by_role
        ws_id = clause.variable_by_role[URI_BDD_PRED_REF_WS][0]
        assert isinstance(ws_id, URIRef)
        ws_id_str = get_valid_var_name(ws_id.n3(ns_manager))

        return f'"<{obj_id_str}>" is located at "<{ws_id_str}>"'

    if URI_BDD_TYPE_IS_HELD in clause.fluent.types:
        assert URI_BDD_PRED_REF_OBJ in clause.variable_by_role
        obj_id = clause.variable_by_role[URI_BDD_PRED_REF_OBJ][0]
        assert isinstance(obj_id, URIRef)
        obj_id_str = get_valid_var_name(obj_id.n3(ns_manager))

        assert URI_BDD_PRED_REF_AGN in clause.variable_by_role
        agn_id = clause.variable_by_role[URI_BDD_PRED_REF_AGN][0]
        assert isinstance(agn_id, URIRef)
        agn_id_str = get_valid_var_name(agn_id.n3(ns_manager))

        return f'"<{obj_id_str}>" is held by "<{agn_id_str}>"'

    raise RuntimeError(
        f"get_clause_str: unhandled types for fluent '{clause.fluent.id}' of clasue '{clause.id}':"
        f" {clause.fluent.types}"
    )


class SceneModel(ModelBase):
    """Assuming the given graph is constructed as a query result from `URL_Q_BDD_US`"""

    objects: Dict[URIRef, set]  # object URI -> obj types
    workspaces: Dict[URIRef, set]  # workspace URI -> ws types
    agents: Dict[URIRef, set]  # agent URI -> agn types

    def __init__(self, us_graph: Graph, full_graph: Graph, scene_id: URIRef) -> None:
        super().__init__(graph=full_graph, node_id=scene_id)
        self.objects = {}
        self.workspaces = {}
        self.agents = {}

        for comp_id in us_graph.objects(subject=scene_id, predicate=URI_BDD_PRED_HAS_SCENE):
            comp_types = set(us_graph.objects(subject=comp_id, predicate=RDF.type))
            assert len(comp_types) > 0, f"composition '{comp_id}' of scene '{scene_id}' has no type"

            if URI_BDD_TYPE_SCENE_OBJ in comp_types:
                for obj_id in full_graph.objects(subject=comp_id, predicate=URI_ENV_PRED_HAS_OBJ):
                    obj_types = set(full_graph.objects(subject=obj_id, predicate=RDF.type))
                    assert isinstance(obj_id, URIRef)
                    self.objects[obj_id] = obj_types

            if URI_BDD_TYPE_SCENE_WS in comp_types:
                for ws_id in full_graph.objects(subject=comp_id, predicate=URI_ENV_PRED_HAS_WS):
                    assert isinstance(ws_id, URIRef)
                    ws_types = set(full_graph.objects(subject=ws_id, predicate=RDF.type))
                    self.workspaces[ws_id] = ws_types

            if URI_BDD_TYPE_SCENE_AGN in comp_types:
                for agn_id in full_graph.objects(subject=comp_id, predicate=URI_AGN_PRED_HAS_AGN):
                    assert isinstance(agn_id, URIRef)
                    agn_types = set(full_graph.objects(subject=agn_id, predicate=RDF.type))
                    self.agents[agn_id] = agn_types


class TaskVariationModel(ModelBase):
    task_id: URIRef
    variables: set[URIRef]
    attributes: dict[URIRef, Any]

    def __init__(self, us_graph: Graph, full_graph: Graph, task_var_id: URIRef) -> None:
        super().__init__(graph=us_graph, node_id=task_var_id)
        task_id = us_graph.value(subject=task_var_id, predicate=URI_TASK_PRED_OF_TASK)
        assert isinstance(task_id, URIRef)
        self.task_id = task_id
        self.variables = set()
        self.attributes = {}

        self._process_builtin_task_var_types(full_graph)

    def _process_builtin_task_var_types(self, full_graph: Graph) -> None:
        if URI_BDD_TYPE_CART_PRODUCT in self.types:
            var_list = self._get_variable_list(graph=full_graph)

            of_sets_list_node = full_graph.value(subject=self.id, predicate=URI_BDD_PRED_OF_SETS)
            assert (
                of_sets_list_node is not None
            ), f"CartesianProductVariation '{self.id}' does not have 'of-sets' property"

            sets_list = []
            for set_node in full_graph.items(list=of_sets_list_node):
                # rdflib doesn't handle container of URIs nicely, so elements are always Literal
                assert isinstance(set_node, Literal)
                set_data = set_node.toPython()
                if isinstance(set_data, list):
                    uri_list = get_uris_from_strings(
                        uri_strings=set_data, ns_manager=full_graph.namespace_manager
                    )
                    sets_list.append(uri_list)
                elif isinstance(set_data, str):
                    try:
                        set_uri = full_graph.namespace_manager.expand_curie(set_data)
                    except ValueError as e:
                        raise ValueError(
                            f"process_task_var: product: failed to parse '{set_data}' as URI: {e}"
                        )
                    sets_list.append(generate_set_values(graph=full_graph, set_uri=set_uri))
                else:
                    raise RuntimeError(f"unhandled type for '{set_node}', type='{type(set_data)}'")

            assert (
                len(sets_list) == len(var_list)
            ), f"length mismatch 'variable-list' (len={len(var_list)}) != 'of-sets' (len={len(sets_list)})"

            self.attributes[URI_BDD_PRED_VAR_LIST] = var_list
            self.attributes[URI_BDD_PRED_OF_SETS] = sets_list

            return

        if URI_BDD_TYPE_TABLE_VAR in self.types:
            var_list = self._get_variable_list(graph=full_graph)
            rows_head = full_graph.value(subject=self.id, predicate=URI_BDD_PRED_ROWS)
            assert (
                rows_head is not None
            ), f"TableVariation '{self.id}' does not have 'rows' property"

            rows = []
            for row_node in full_graph.items(list=rows_head):
                assert isinstance(row_node, Literal)
                row_data = row_node.toPython()
                assert isinstance(
                    row_data, list
                ), f"TableVariation '{self.id}': row data not a list: {row_data}"
                assert (
                    len(row_data) == len(var_list)
                ), f"TableVariation '{self.id}': row length does not match variable list: {row_data}"

                row_uris = []
                for uri_str in row_data:
                    try:
                        uri = full_graph.namespace_manager.expand_curie(uri_str)
                    except ValueError as e:
                        raise ValueError(
                            f"process_task_var: table: failed to parse '{uri_str}' as URI: {e}"
                        )

                    row_uris.append(uri)

                rows.append(row_uris)

            self.attributes[URI_BDD_PRED_VAR_LIST] = var_list
            self.attributes[URI_BDD_PRED_ROWS] = rows

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


def generate_set_values(graph: Graph, set_uri: URIRef) -> list[URIRef]:
    set_types = set(graph.objects(subject=set_uri, predicate=RDF.type))
    if URI_BDD_TYPE_COMBINATION in set_types:
        rep_allowed = graph.value(subject=set_uri, predicate=URI_BDD_PRED_REP_ALLOWED)
        assert (
            rep_allowed is not None
            and isinstance(rep_allowed, Literal)
            and isinstance(rep_allowed.value, bool)
        ), f"Combination '{set_uri}' does not have bool literal 'repetition-allowed' property: {rep_allowed}"
        rep_allowed = rep_allowed.value

        select_num = graph.value(subject=set_uri, predicate=URI_BDD_PRED_SELECT)
        assert (
            select_num is not None
            and isinstance(select_num, Literal)
            and isinstance(select_num.value, int)
        ), f"Combination '{set_uri}' does not have int literal 'select' property: {select_num}"
        select_num = select_num.value
        assert (
            select_num > 0
        ), f"Combination '{set_uri}': 'select' property is non-positive: {select_num}"

        from_list_head = graph.value(subject=set_uri, predicate=URI_BDD_PRED_FROM)
        assert from_list_head is not None, f"Combination '{set_uri}' does not have 'from' property"
        from_list = []
        for uri in graph.items(list=from_list_head):
            assert isinstance(uri, URIRef)
            from_list.append(uri)

        assert (
            select_num <= len(from_list)
        ), f"Combination '{set_uri}': 'select'(={select_num}) is larger than length of 'from' (len={len(from_list)})"
        set_values = []
        for comb in combinations(from_list, select_num):
            # TODO(minhnh): itertool does not consider repetitions, rep_allowed is unused
            if select_num == 1:
                set_values.append(comb[0])
            else:
                set_values.append(comb)

        return set_values

    raise RuntimeError(f"unhandled types for set '{set_uri}': {set_types}")


def get_uris_from_strings(uri_strings: list, ns_manager: NamespaceManager) -> list[URIRef]:
    uri_list = []
    for uri_str in uri_strings:
        try:
            uri = ns_manager.expand_curie(uri_str)
        except ValueError as e:
            raise ValueError(f"uri_from_strings: failed to parse '{uri_str}' as URI: {e}")

        uri_list.append(uri)

    return uri_list


class ScenarioVariantModel(ModelBase):
    """Assuming the given graph is constructed as a query result from `URL_Q_BDD_US`"""

    us_id: URIRef
    scenario_id: URIRef
    tmpl_id: URIRef
    given_id: URIRef
    when_id: URIRef
    then_id: URIRef
    bhv_id: URIRef
    task_id: URIRef
    scene: SceneModel
    task_variation: TaskVariationModel
    variables: set[URIRef]  # set of ScenarioVariables referred to by clauses
    _clauses: Dict[URIRef, FluentClauseModel]
    _clauses_by_role: Dict[URIRef, set[URIRef]]  # given/when/then URI -> clause URI
    _tmpl_clauses: set[URIRef]
    _variant_clauses: set[URIRef]

    def __init__(self, us_graph: Graph, full_graph: Graph, var_id: URIRef) -> None:
        super().__init__(graph=us_graph, node_id=var_id)

        node_val = us_graph.value(subject=var_id, predicate=URI_BDD_PRED_OF_SCENARIO)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"ScenarioVariant '{var_id}' does not refer to a Scenario"
        self.scenario_id = node_val

        node_val = us_graph.value(subject=var_id, predicate=URI_BDD_PRED_OF_TMPL)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"ScenarioVariant '{var_id}' does not refer to a ScenarioTemplate"
        self.tmpl_id = node_val

        node_val = us_graph.value(subject=var_id, predicate=URI_BDD_PRED_GIVEN)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"ScenarioVariant '{var_id}' does not refer to a Given"
        self.given_id = node_val

        node_val = us_graph.value(subject=var_id, predicate=URI_BDD_PRED_WHEN)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"ScenarioVariant '{var_id}' does not refer to a When"
        self.when_id = node_val

        node_val = us_graph.value(subject=var_id, predicate=URI_BDD_PRED_THEN)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"ScenarioVariant '{var_id}' does not refer to a Then"
        self.then_id = node_val

        node_val = us_graph.value(subject=var_id, predicate=URI_BHV_PRED_OF_BHV)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"ScenarioVariant '{var_id}' does not refer to a Behaviour"
        self.bhv_id = node_val

        node_val = us_graph.value(subject=var_id, predicate=URI_TASK_PRED_OF_TASK)
        assert node_val is not None and isinstance(
            node_val, URIRef
        ), f"ScenarioVariant '{var_id}' does not refer to a Task"
        self.task_id = node_val

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

        self._clauses = {}
        self._clauses_by_role = {self.given_id: set(), self.when_id: set(), self.then_id: set()}
        self._tmpl_clauses = set()
        self._variant_clauses = set()
        self.variables = set()

        self._load_clauses(full_graph)

        task_var_id = us_graph.value(subject=var_id, predicate=URI_BDD_PRED_HAS_VARIATION)
        assert task_var_id is not None and isinstance(
            task_var_id, URIRef
        ), f"ScenarioVariant '{var_id}' does not refer to a TaskVariation"
        self.task_variation = TaskVariationModel(
            us_graph=us_graph, full_graph=full_graph, task_var_id=task_var_id
        )
        assert self.task_variation.variables == self.variables, (
            f"variables referred to by clauses in ScenarioVariant '{self.id}'"
            f" does not match that of TaskVariation '{self.task_variation.id}':\n"
            f"clause vars: {self.variables}\ntask variation vars: {self.task_variation.variables}"
        )

    def _load_clauses(self, full_graph: Graph) -> None:
        """
        Load all fluent clauses attached to both the ScenarioVariant and ScenarioTemplate in the graph.
        This will also update the set of variables referred to by these clauses
        """
        # template clauses
        for clause_id in full_graph.objects(
            subject=self.tmpl_id, predicate=URI_BDD_PRED_HAS_CLAUSE
        ):
            assert isinstance(clause_id, URIRef)
            assert clause_id not in self._tmpl_clauses, f"Duplicate template clause '{clause_id}'"
            self._tmpl_clauses.add(clause_id)
            self._load_single_clause(full_graph, clause_id)

        # variant clauses
        for clause_id in full_graph.objects(subject=self.id, predicate=URI_BDD_PRED_HAS_CLAUSE):
            assert isinstance(clause_id, URIRef)
            assert clause_id not in self._variant_clauses, f"Duplicate variant clause '{clause_id}'"
            self._variant_clauses.add(clause_id)
            self._load_single_clause(full_graph, clause_id)

    def _load_single_clause(self, full_graph: Graph, clause_id: URIRef):
        assert clause_id not in self._clauses, f"Duplicate clause '{clause_id}'"
        clause = FluentClauseModel(full_graph=full_graph, clause_id=clause_id)
        assert (
            clause.clause_of in self._clauses_by_role
        ), f"Clause '{clause_id}' not connected to Given, When, Then of Scenario '{self.scenario_id}'"
        assert clause_id not in self._clauses_by_role[clause.clause_of]

        self._clauses[clause_id] = clause
        self._clauses_by_role[clause.clause_of].add(clause_id)
        for var_id in clause.role_by_variable.keys():
            self.variables.add(var_id)

    def get_given_clause_models(self) -> Generator[FluentClauseModel, None, None]:
        for given_clause_id in self._clauses_by_role[self.given_id]:
            yield self._clauses[given_clause_id]

    def get_then_clause_models(self) -> Generator[FluentClauseModel, None, None]:
        for then_clause_id in self._clauses_by_role[self.then_id]:
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

    def get_us_scenario_variants(self) -> Dict[URIRef, set[URIRef]]:
        """
        returns { <UserStory URI> : [ <list of ScenarioVariant URIs> ] }
        """
        q_result = self._us_graph.query(Q_US_VAR)
        assert q_result.type == "SELECT" and isinstance(q_result, Iterable)

        us_var_dict = {}
        for row in q_result:
            assert isinstance(row, ResultRow)
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
