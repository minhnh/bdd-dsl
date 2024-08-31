# SPDX-License-Identifier:  GPL-3.0-or-later
from rdflib import URIRef, Graph, RDF


class ModelBase(object):
    """All models should have an URI as ID and types"""

    id: URIRef
    types: set[URIRef]

    def __init__(self, graph: Graph, node_id: URIRef) -> None:
        self.id = node_id
        self.types = set()
        for type_id in graph.objects(subject=node_id, predicate=RDF.type):
            assert isinstance(type_id, URIRef)
            self.types.add(type_id)

        assert len(self.types) > 0
