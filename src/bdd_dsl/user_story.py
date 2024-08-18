# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Any
from rdflib import RDF, Graph, URIRef
from bdd_dsl.models.queries import Q_USER_STORY
from bdd_dsl.models.urirefs import (
    URI_BDD_TYPE_SCENE_AGN,
    URI_BDD_TYPE_SCENE_OBJ,
    URI_BDD_PRED_HAS_SCENE,
    URI_BDD_PRED_OF_SCENARIO,
    URI_BDD_PRED_OF_TMPL,
    URI_BDD_PRED_HAS_AC,
    URI_BDD_TYPE_SCENE_WS,
    URI_BHV_PRED_OF_BHV,
    URI_ENV_PRED_HAS_OBJ,
    URI_ENV_PRED_HAS_WS,
    URI_AGN_PRED_HAS_AGN,
)


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

    def __init__(self, us_graph: Graph, full_graph: Graph, var_id: URIRef) -> None:
        self.id = var_id

        self.scenario_id = us_graph.value(subject=var_id, predicate=URI_BDD_PRED_OF_SCENARIO)
        assert (
            self.scenario_id is not None
        ), f"ScenarioVariant '{var_id}' does not refer to a Scenario"

        self.tmpl_id = us_graph.value(subject=var_id, predicate=URI_BDD_PRED_OF_TMPL)
        assert (
            self.tmpl_id is not None
        ), f"ScenarioVariant '{var_id}' does not refer to a ScenarioTemplate"

        self.bhv_id = us_graph.value(subject=var_id, predicate=URI_BHV_PRED_OF_BHV)
        assert self.bhv_id is not None, f"ScenarioVariant '{var_id}' does not refer to a Behaviour"

        scene_id = us_graph.value(subject=var_id, predicate=URI_BDD_PRED_HAS_SCENE)
        assert scene_id is not None, f"ScenarioVariant '{var_id}' does not refer to a Scene"
        assert isinstance(scene_id, URIRef)
        self.scene = SceneModel(us_graph=us_graph, full_graph=full_graph, scene_id=scene_id)

        us_ids = list(us_graph.subjects(object=var_id, predicate=URI_BDD_PRED_HAS_AC))
        assert (
            len(us_ids) == 1
        ), f"ScenarioVariant 'var_id' does not refer to exactly 1 UserStory, found: {us_ids}"
        self.us_id = us_ids[0]


class UserStoryLoader(object):
    def __init__(self, graph: Graph, **kwargs: Any) -> None:
        q_result = graph.query(Q_USER_STORY)
        assert q_result.type == "CONSTRUCT" and q_result.graph is not None
        self._us_graph = q_result.graph
        print(self._us_graph.serialize(format="json-ld"))

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
