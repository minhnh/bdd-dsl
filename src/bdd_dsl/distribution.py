# SPDX-License-Identifier:  GPL-3.0-or-later
from rdflib import Graph, URIRef, RDF
from bdd_dsl.models.urirefs import URI_DISTRIB_FROM_DISTRIBUTION


KEY_SAMPLED_QTY = "sampled quantity"


class DistributionData(object):
    def __init__(self, graph: Graph, distrib_id: URIRef) -> None:
        self.id = distrib_id
        self.types = list(graph.objects(subject=distrib_id, predicate=RDF.type))
        assert len(self.types) > 0


class SampledQuantityData(object):
    def __init__(self, graph: Graph, quantity_id: URIRef) -> None:
        self.id = quantity_id
        distrib_id = graph.value(subject=quantity_id, predicate=URI_DISTRIB_FROM_DISTRIBUTION)
        assert (
            distrib_id is not None
        ), f"SampledQuantity '{quantity_id}' does not map to a Distribution"
        assert isinstance(distrib_id, URIRef)

        self.distribution = DistributionData(graph=graph, distrib_id=distrib_id)
