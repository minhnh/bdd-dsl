# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Dict, Generator, Iterable
from rdflib import RDF, Graph, URIRef
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
    URI_BDD_PRED_GIVEN,
    URI_BDD_PRED_HAS_CLAUSE,
    URI_BDD_PRED_HAS_VARIATION,
    URI_BDD_PRED_HOLDS,
    URI_BDD_PRED_HOLDS_AT,
    URI_BDD_PRED_REF_AGN,
    URI_BDD_PRED_REF_OBJ,
    URI_BDD_PRED_REF_WS,
    URI_BDD_PRED_THEN,
    URI_BDD_PRED_WHEN,
    URI_BDD_TYPE_IS_HELD,
    URI_BDD_TYPE_LOCATED_AT,
    URI_BDD_TYPE_SCENE_AGN,
    URI_BDD_TYPE_SCENE_OBJ,
    URI_BDD_PRED_HAS_SCENE,
    URI_BDD_PRED_OF_SCENARIO,
    URI_BDD_PRED_OF_TMPL,
    URI_BDD_PRED_HAS_AC,
    URI_BDD_TYPE_SCENE_WS,
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

    def add_variable_role(self, full_graph: Graph, role_pred: URIRef):
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
            self.add_variable_role(full_graph=full_graph, role_pred=URI_BDD_PRED_REF_OBJ)
            if len(self.variable_by_role[URI_BDD_PRED_REF_OBJ]) != 1:
                raise BDDConstraintViolation(
                    f"Fluent '{self.fluent.id}' of clause '{self.id}', type 'LocatedAt',"
                    f" does not refer to exactly 1 object: {self.variable_by_role[URI_BDD_PRED_REF_OBJ]}"
                )

            self.add_variable_role(full_graph=full_graph, role_pred=URI_BDD_PRED_REF_WS)
            if len(self.variable_by_role[URI_BDD_PRED_REF_WS]) != 1:
                raise BDDConstraintViolation(
                    f"Fluent '{self.fluent.id}' of clause '{self.id}', type 'LocatedAt',"
                    f" does not refer to exactly 1 workspace: {self.variable_by_role[URI_BDD_PRED_REF_WS]}"
                )

            return

        if URI_BDD_TYPE_IS_HELD in self.fluent.types:
            self.add_variable_role(full_graph=full_graph, role_pred=URI_BDD_PRED_REF_OBJ)
            if len(self.variable_by_role[URI_BDD_PRED_REF_OBJ]) != 1:
                raise BDDConstraintViolation(
                    f"Fluent '{self.fluent.id}' of clause '{self.id}', type 'IsHeld',"
                    f" does not refer to exactly 1 object: {self.variable_by_role[URI_BDD_PRED_REF_OBJ]}"
                )

            self.add_variable_role(full_graph=full_graph, role_pred=URI_BDD_PRED_REF_AGN)
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
    def __init__(self, us_graph: Graph, full_graph: Graph, task_var_id: URIRef) -> None:
        super().__init__(graph=us_graph, node_id=task_var_id)


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
