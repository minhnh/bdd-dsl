# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Iterator
import itertools
from rdflib import Graph, URIRef, Literal
from rdf_utils.models.common import ModelBase
from bdd_dsl.models.namespace import NS_MM_BDD
from bdd_dsl.models.urirefs import URI_BDD_PRED_ELEMS, URI_BDD_TYPE_CONST_SET


URI_BDD_TYPE_COMBINATION = NS_MM_BDD["Combination"]
URI_BDD_TYPE_PERMUTATION = NS_MM_BDD["Permutation"]
URI_BDD_PRED_FROM = NS_MM_BDD["from"]
URI_BDD_PRED_REP_ALLOWED = NS_MM_BDD["repetition-allowed"]
URI_BDD_PRED_LENGTH = NS_MM_BDD["length"]


class SetEnumerationModel(ModelBase):
    """Model for handling simple enumeration of a set, namely combinations and permutations."""

    enumeration_type: URIRef

    def __init__(self, node_id: URIRef, graph: Graph) -> None:
        super().__init__(node_id=node_id, graph=graph)

        if URI_BDD_TYPE_COMBINATION in self.types:
            self.enumeration_type = URI_BDD_TYPE_COMBINATION
        elif URI_BDD_TYPE_PERMUTATION in self.types:
            self.enumeration_type = URI_BDD_TYPE_PERMUTATION
        else:
            raise RuntimeError(f"SetEnumeration: unhandled types for '{self.id}': {self.types}")

        # if not specified, repetition is not allowed
        rep_allowed_node = graph.value(subject=self.id, predicate=URI_BDD_PRED_REP_ALLOWED)
        if rep_allowed_node is None:
            rep_allowed = False
        else:
            assert isinstance(
                rep_allowed_node, Literal
            ), f"SetEnumeration: '{self.id}' does not have literal 'repetition-allowed' property: {rep_allowed_node}"
            rep_allowed = rep_allowed_node.toPython()
            assert isinstance(
                rep_allowed, bool
            ), f"SetEnumeration: '{self.id}' does not have boolean 'repetition-allowed': {rep_allowed_node}"
        self.set_attr(key=URI_BDD_PRED_REP_ALLOWED, val=rep_allowed)

        # set to enumerate
        from_node = graph.value(subject=self.id, predicate=URI_BDD_PRED_FROM)
        assert isinstance(
            from_node, URIRef
        ), f"SetEnumeration: '{self.id}' does not link to URIRef via a 'from' property"

        set_model = ModelBase(node_id=from_node, graph=graph)
        assert (
            URI_BDD_TYPE_CONST_SET in set_model.types
        ), f"type(s) not handled for Set {set_model.id}: {set_model.types}"
        from_list = []
        for elem in graph.objects(subject=set_model.id, predicate=URI_BDD_PRED_ELEMS):
            from_list.append(elem)
        self.set_attr(key=URI_BDD_PRED_FROM, val=from_list)

        # if no length specified, set to length of list
        length_node = graph.value(subject=self.id, predicate=URI_BDD_PRED_LENGTH)
        if length_node is None:
            length = len(from_list)
        else:
            assert isinstance(
                length_node, Literal
            ), f"SetEnumeration: '{self.id}' does not have int literal 'from' property: {length_node}"
            length = length_node.toPython()
            assert (
                isinstance(length, int) and length > 0
            ), f"SetEnumeration: '{self.id}': 'length' property is not a positive integer: {length}"

        assert length <= len(
            from_list
        ), f"SetEnumeration '{self.id}': 'length'(={length}) > set size(={len(from_list)})"
        self.set_attr(key=URI_BDD_PRED_LENGTH, val=length)

    def enumerate(self) -> Iterator:
        from_list = self.get_attr(key=URI_BDD_PRED_FROM)
        length = self.get_attr(key=URI_BDD_PRED_LENGTH)
        rep_allowed = self.get_attr(key=URI_BDD_PRED_REP_ALLOWED)
        assert (
            isinstance(from_list, list)
            and isinstance(length, int)
            and isinstance(rep_allowed, bool)
        ), f"SetEnumeration.enumerate: '{self.id}' does not have expected attributes"

        if self.enumeration_type == URI_BDD_TYPE_COMBINATION:
            if rep_allowed:
                return itertools.combinations_with_replacement(from_list, r=length)
            return itertools.combinations(from_list, r=length)

        if self.enumeration_type == URI_BDD_TYPE_PERMUTATION:
            # repetition is not handled by itertools for permutations
            return itertools.permutations(from_list, r=length)

        raise RuntimeError(f"SetEnumeration.enumerate: '{self.id}' has no handled enumeration type")
