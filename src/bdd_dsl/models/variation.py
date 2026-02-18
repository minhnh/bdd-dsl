# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Any, Iterable, Iterator
import itertools
from rdflib import BNode, Graph, URIRef, Literal
from rdf_utils.collection import load_list_re
from rdf_utils.models.common import ModelBase, get_node_types
from bdd_dsl.models.namespace import NS_MM_BDD
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_ELEMS,
    URI_BDD_PRED_OF_SETS,
    URI_BDD_PRED_ROWS,
    URI_BDD_PRED_VAR_LIST,
    URI_BDD_TYPE_CART_PRODUCT,
    URI_BDD_TYPE_CONST_SET,
    URI_BDD_TYPE_TABLE_VAR,
    URI_TASK_PRED_OF_TASK,
)


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


class TaskVariationModel(ModelBase):
    task_id: URIRef
    variables: set[URIRef]
    set_enums: dict[URIRef, SetEnumerationModel]
    const_sets: dict[URIRef, list[Any]]

    def __init__(self, us_graph: Graph, full_graph: Graph, task_var_id: URIRef) -> None:
        super().__init__(graph=us_graph, node_id=task_var_id)
        task_id = us_graph.value(subject=task_var_id, predicate=URI_TASK_PRED_OF_TASK)
        assert isinstance(task_id, URIRef), f"task_id is not URIRef: type={type(task_id)}"
        self.task_id = task_id
        self.variables = set()
        self.set_enums = {}
        self.const_sets = {}

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
            ), f"Cart Product '{self.id}': length mismatch 'variable-list' (len={len(var_list)}) != 'of-sets' (len={len(sets_list)})"

            for sets_data in sets_list:
                if isinstance(sets_data, list):
                    continue

                assert isinstance(
                    sets_data, URIRef
                ), f"TaskVariation '{self.id}': unexpected sets type for: {sets_data}"

                # if set URI already processed
                if sets_data in self.const_sets or sets_data in self.set_enums:
                    continue

                sets_data_types = get_node_types(graph=full_graph, node_id=sets_data)

                # constant sets
                if URI_BDD_TYPE_CONST_SET in sets_data_types:
                    sd_list = []
                    for elem in full_graph.objects(subject=sets_data, predicate=URI_BDD_PRED_ELEMS):
                        sd_list.append(elem)
                    self.const_sets[sets_data] = sd_list
                    continue

                # set enumerations
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


def get_task_variations(task_var: TaskVariationModel) -> tuple[list[URIRef], list[Iterable[Any]]]:
    var_uri_list = task_var.get_attr(key=URI_BDD_PRED_VAR_LIST)
    assert isinstance(
        var_uri_list, list
    ), f"TaskVariation '{task_var.id}' does not have a list of variables as attr"

    if URI_BDD_TYPE_CART_PRODUCT in task_var.types:
        var_value_sets = task_var.get_attr(key=URI_BDD_PRED_OF_SETS)
        assert isinstance(
            var_value_sets, list
        ), f"TaskVariation '{task_var.id}' does not have a list of variable values as attr"
        assert len(var_uri_list) == len(
            var_value_sets
        ), f"TaskVariation '{task_var.id}': number of varibles doesn't match set of values"

        uri_iterables = []
        for set_data in var_value_sets:
            if isinstance(set_data, URIRef):
                if set_data in task_var.const_sets:
                    uri_iterables.append(list(task_var.const_sets[set_data]))
                elif set_data in task_var.set_enums:
                    set_data_vals = list(task_var.set_enums[set_data].enumerate())
                    uri_iterables.append(set_data_vals)
                else:
                    raise RuntimeError(
                        f"unhandled set URI '{set_data}' for variation '{task_var.id}'"
                    )
            elif isinstance(set_data, list):
                # list
                uri_iterables.append(set_data)
            else:
                raise RuntimeError(
                    f"TaskVariation {task_var.id}: sets for cartesian product not list or URIRef: {set_data}"
                )

        return var_uri_list, list(itertools.product(*uri_iterables))

    if URI_BDD_TYPE_TABLE_VAR in task_var.types:
        uri_rows = task_var.get_attr(key=URI_BDD_PRED_ROWS)
        assert isinstance(
            uri_rows, list
        ), f"TaskVariation {task_var.id}: table rows are not a list: {uri_rows}"
        return var_uri_list, uri_rows

    raise RuntimeError(f"TaskVariation '{task_var.id}' has unhandled types: {task_var.types}")


def get_task_var_dicts(task_var: TaskVariationModel) -> list[dict[URIRef, Any]]:
    var_uri_list, var_value_sets = get_task_variations(task_var=task_var)
    return [dict(zip(var_uri_list, val_set)) for val_set in var_value_sets]
