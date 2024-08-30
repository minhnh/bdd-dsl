# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Dict, Iterable, Set
from rdflib import RDF, Graph, URIRef
from rdflib.query import ResultRow
from bdd_dsl.models.queries import Q_USER_STORY
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_CLAUSE_OF,
    URI_BDD_PRED_GIVEN,
    URI_BDD_PRED_HAS_CLAUSE,
    URI_BDD_PRED_HOLDS,
    URI_BDD_PRED_HOLDS_AT,
    URI_BDD_PRED_THEN,
    URI_BDD_PRED_WHEN,
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
)


Q_US_VAR = f"""
SELECT DISTINCT ?us ?var WHERE {{
    ?us a {URI_BDD_TYPE_US.n3()} .
    ?us {URI_BDD_PRED_HAS_AC.n3()} ?var .
}}
"""


class FluentModel(object):
    id: URIRef
    types: set

    def __init__(self, full_graph: Graph, fluent_id: URIRef) -> None:
        self.id = fluent_id
        self.types = set(full_graph.objects(subject=fluent_id, predicate=RDF.type))
        assert len(self.types) > 0


class TimeConstraintModel(object):
    id: URIRef
    types: set

    def __init__(self, full_graph: Graph, tc_id: URIRef) -> None:
        self.id = tc_id
        self.types = set(full_graph.objects(subject=tc_id, predicate=RDF.type))
        assert len(self.types) > 0


class FluentClauseModel(object):
    id: URIRef
    clause_of: URIRef
    fluent: FluentModel
    time_constraint: TimeConstraintModel

    def __init__(self, full_graph: Graph, clause_id: URIRef) -> None:
        self.id = clause_id

        clause_of_id = full_graph.value(subject=clause_id, predicate=URI_BDD_PRED_CLAUSE_OF)
        assert isinstance(clause_of_id, URIRef)
        self.clause_of = clause_of_id

        fluent_id = full_graph.value(subject=clause_id, predicate=URI_BDD_PRED_HOLDS)
        assert isinstance(fluent_id, URIRef)
        self.fluent = FluentModel(full_graph=full_graph, fluent_id=fluent_id)

        tc_id = full_graph.value(subject=clause_id, predicate=URI_BDD_PRED_HOLDS_AT)
        assert isinstance(tc_id, URIRef)
        self.time_constraint = TimeConstraintModel(full_graph=full_graph, tc_id=tc_id)


class SceneModel(object):
    """Assuming the given graph is constructed as a query result from `URL_Q_BDD_US`"""

    def __init__(self, us_graph: Graph, full_graph: Graph, scene_id: URIRef) -> None:
        self.id = scene_id
        self.objects = {}  # object URI -> obj types
        self.workspaces = {}  # workspace URI -> ws types
        self.agents = {}  # agent URI -> agn types

        for comp_id in us_graph.objects(subject=scene_id, predicate=URI_BDD_PRED_HAS_SCENE):
            comp_types = set(us_graph.objects(subject=comp_id, predicate=RDF.type))
            assert len(comp_types) > 0, f"composition '{comp_id}' of scene '{scene_id}' has no type"

            if URI_BDD_TYPE_SCENE_OBJ in comp_types:
                for obj_id in full_graph.objects(subject=comp_id, predicate=URI_ENV_PRED_HAS_OBJ):
                    obj_types = set(full_graph.objects(subject=obj_id, predicate=RDF.type))
                    self.objects[obj_id] = obj_types

            if URI_BDD_TYPE_SCENE_WS in comp_types:
                for ws_id in full_graph.objects(subject=comp_id, predicate=URI_ENV_PRED_HAS_WS):
                    ws_types = set(full_graph.objects(subject=ws_id, predicate=RDF.type))
                    self.workspaces[ws_id] = ws_types

            if URI_BDD_TYPE_SCENE_AGN in comp_types:
                for agn_id in full_graph.objects(subject=comp_id, predicate=URI_AGN_PRED_HAS_AGN):
                    agn_types = set(full_graph.objects(subject=agn_id, predicate=RDF.type))
                    self.agents[agn_id] = agn_types


class ScenarioVariantModel(object):
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

    def __init__(self, us_graph: Graph, full_graph: Graph, var_id: URIRef) -> None:
        self.id = var_id

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
        self._load_clauses(full_graph)

    def _load_clauses(self, full_graph: Graph) -> None:
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

        self._clauses[clause_id] = clause


class UserStoryLoader(object):
    def __init__(self, graph: Graph) -> None:
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

    def get_us_scenario_variants(self) -> Dict[URIRef, Set[URIRef]]:
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
