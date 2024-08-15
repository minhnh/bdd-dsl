# SPDX-License-Identifier:  GPL-3.0-or-later
from abc import ABC, abstractmethod
from typing import Any, Optional
from behave.runner import Context
from rdflib import RDF, Graph, URIRef
from rdf_utils.uri import URL_SECORO_M
from rdf_utils.caching import read_url_and_cache
from rdf_utils.python import URI_PY_TYPE_MODULE_ATTR, import_attr_from_node
from bdd_dsl.models.urirefs import URI_BDD_TYPE_BHV_IMPL, URI_BHV_PRED_OF_BHV


URL_Q_SCENARIO_EXEC = f"{URL_SECORO_M}/acceptance-criteria/bdd/queries/scenario-execution.rq"


class Behaviour(ABC):
    @abstractmethod
    def __init__(self, context: Context, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def is_finished(self, context: Context, **kwargs: Any) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def reset(self, context: Context, **kwargs: Any) -> None:
        raise NotImplementedError()

    @abstractmethod
    def step(self, context: Context, **kwargs: Any) -> Any:
        raise NotImplementedError()


class BehaviourImplModel(object):
    behaviour: Optional[Behaviour]

    def __init__(self, graph: Graph, bhv_impl_uri: URIRef, context: Context, **kwargs: Any) -> None:
        self.id = bhv_impl_uri
        self.types = set(graph.objects(subject=self.id, predicate=RDF.type))
        self.behaviour = None
        self.handled_type = None

        assert URI_BDD_TYPE_BHV_IMPL in self.types

        if URI_PY_TYPE_MODULE_ATTR in self.types:
            self.handled_type = URI_PY_TYPE_MODULE_ATTR
            bhv_cls = import_attr_from_node(graph=graph, uri=self.id)
            assert issubclass(bhv_cls, Behaviour), f"expects extension of '{Behaviour}'"
            self.behaviour = bhv_cls(context=context, **kwargs)

        assert (
            self.handled_type is not None
        ), f"BehaviourImplModel: unhandled type for '{self.id}': {self.types}"
        assert self.behaviour is not None


class ExecutionModel(object):
    def __init__(self, graph: Graph) -> None:
        g_query_str = read_url_and_cache(URL_Q_SCENARIO_EXEC)
        q_result = graph.query(g_query_str)
        assert q_result.type == "CONSTRUCT"
        assert q_result.graph is not None

        self._graph = graph
        self._scenario_exec_graph = q_result.graph

        for prefix, uri in graph.namespaces():
            self._scenario_exec_graph.bind(prefix=prefix, namespace=uri, override=True)

        self._bhv_impl = {}

    @property
    def scenario_exec_graph(self) -> Graph:
        return self._scenario_exec_graph

    def load_behaviour_impl(self, context: Context, bhv_id: str) -> BehaviourImplModel:
        if bhv_id in self._bhv_impl:
            return self._bhv_impl[bhv_id]

        try:
            bhv_uri = self._scenario_exec_graph.namespace_manager.expand_curie(bhv_id)
        except ValueError as e:
            raise RuntimeError(f"can't parse behaviour URI '{bhv_id}': {e}")

        bhv_impl_ids = list(
            self._scenario_exec_graph.subjects(object=bhv_uri, predicate=URI_BHV_PRED_OF_BHV)
        )
        assert (
            len(bhv_impl_ids) == 1
        ), f"not exactly 1 implementation found for '{bhv_id}', found: {bhv_impl_ids}"
        assert isinstance(bhv_impl_ids[0], URIRef)

        bhv_impl = BehaviourImplModel(
            graph=self._graph, bhv_impl_uri=bhv_impl_ids[0], context=context
        )
        self._bhv_impl[bhv_id] = bhv_impl
        return bhv_impl
