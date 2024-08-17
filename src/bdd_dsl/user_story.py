# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Any
from rdflib import RDF, Graph, URIRef
from bdd_dsl.models.queries import Q_USER_STORY
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_HAS_SCENE,
    URI_BDD_PRED_OF_SCENARIO,
    URI_BDD_PRED_OF_TMPL,
    URI_BDD_PRED_HAS_AC,
    URI_BHV_PRED_OF_BHV,
)


class SceneModel(object):
    """Assuming the given graph is constructed as a query result from `URL_Q_BDD_US`"""

    def __init__(self, graph: Graph, scene_id: URIRef) -> None:
        self.elem_types = set(graph.objects(subject=scene_id, predicate=RDF.type))


class ScenarioVariantModel(object):
    """Assuming the given graph is constructed as a query result from `URL_Q_BDD_US`"""

    def __init__(self, graph: Graph, var_id: URIRef) -> None:
        self.id = var_id

        self.scenario_id = graph.value(subject=var_id, predicate=URI_BDD_PRED_OF_SCENARIO)
        assert (
            self.scenario_id is not None
        ), f"ScenarioVariant '{var_id}' does not refer to a Scenario"

        self.tmpl_id = graph.value(subject=var_id, predicate=URI_BDD_PRED_OF_TMPL)
        assert (
            self.tmpl_id is not None
        ), f"ScenarioVariant '{var_id}' does not refer to a ScenarioTemplate"

        self.bhv_id = graph.value(subject=var_id, predicate=URI_BHV_PRED_OF_BHV)
        assert self.bhv_id is not None, f"ScenarioVariant '{var_id}' does not refer to a Behaviour"

        scene_id = graph.value(subject=var_id, predicate=URI_BDD_PRED_HAS_SCENE)
        assert scene_id is not None, f"ScenarioVariant '{var_id}' does not refer to a Scene"
        assert isinstance(scene_id, URIRef)
        self.scene = SceneModel(graph=graph, scene_id=scene_id)

        us_ids = list(graph.subjects(object=var_id, predicate=URI_BDD_PRED_HAS_AC))
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

    def load_scenario_variant(self, variant_id: URIRef) -> ScenarioVariantModel:
        if variant_id in self._scenario_variants:
            return self._scenario_variants[variant_id]

        var_model = ScenarioVariantModel(graph=self._us_graph, var_id=variant_id)
        self._scenario_variants[variant_id] = var_model
        return var_model
