# SPDX-License-Identifier:  GPL-3.0-or-later
from abc import ABC, abstractmethod
from typing import Any, Optional
from rdflib import Graph, URIRef
from behave.runner import Context
from rdf_utils.models.common import ModelBase, get_node_types
from bdd_dsl.models.urirefs import URI_BHV_PRED_OF_BHV


class Behaviour(ModelBase, ABC):
    @abstractmethod
    def __init__(
        self, bhv_id: URIRef, bhv_types: set[URIRef], context: Context, **kwargs: Any
    ) -> None:
        ModelBase.__init__(self, node_id=bhv_id, types=bhv_types)

    @abstractmethod
    def is_finished(self, context: Context, **kwargs: Any) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def reset(self, context: Context, **kwargs: Any) -> None:
        raise NotImplementedError()

    @abstractmethod
    def step(self, context: Context, **kwargs: Any) -> Any:
        raise NotImplementedError()


class BehaviourImplModel(ModelBase):
    behaviour: Optional[Behaviour]
    behaviour_uri: URIRef
    behaviour_types: set[URIRef]

    def __init__(self, graph: Graph, bhv_impl_id: URIRef) -> None:
        super().__init__(graph=graph, node_id=bhv_impl_id)
        self.behaviour = None

        bhv_uri = graph.value(subject=self.id, predicate=URI_BHV_PRED_OF_BHV)
        assert isinstance(bhv_uri, URIRef), (
            f"BehaviourImpl '{self.id}' doesn't ref a Behaviour URI: {bhv_uri}"
        )
        self.behaviour_uri = bhv_uri

        self.behaviour_types = get_node_types(graph=graph, node_id=self.behaviour_uri)
        assert len(self.behaviour_types) > 0, f"No types found for Behaviour '{self.behaviour_uri}'"
