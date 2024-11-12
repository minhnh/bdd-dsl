# SPDX-License-Identifier:  GPL-3.0-or-later
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from behave.runner import Context
from rdf_utils.models.common import ModelBase, ModelLoader
from rdflib import Graph, URIRef
from rdf_utils.uri import URL_SECORO_M
from rdf_utils.caching import read_url_and_cache
from rdf_utils.models.python import (
    URI_PY_TYPE_MODULE_ATTR,
    import_attr_from_model,
    load_py_module_attr,
)
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


class BehaviourImplModel(ModelBase):
    behaviour: Optional[Behaviour]

    def __init__(self, graph: Graph, bhv_impl_uri: URIRef) -> None:
        super().__init__(graph=graph, node_id=bhv_impl_uri)
        self.behaviour = None

        assert URI_BDD_TYPE_BHV_IMPL in self.types


class ExecutionModel(object):
    bhv_model_loader: ModelLoader
    _scenario_exec_graph: Graph
    _bhv_impl: Dict[URIRef, BehaviourImplModel]

    def __init__(self, graph: Graph) -> None:
        g_query_str = read_url_and_cache(URL_Q_SCENARIO_EXEC)
        q_result = graph.query(g_query_str)
        assert q_result.type == "CONSTRUCT"
        assert q_result.graph is not None

        self._scenario_exec_graph = q_result.graph

        for prefix, uri in graph.namespaces():
            self._scenario_exec_graph.bind(prefix=prefix, namespace=uri, override=True)

        self._bhv_impl = {}
        self.bhv_model_loader = ModelLoader()
        self.bhv_model_loader.register(load_py_module_attr)

    @property
    def scenario_exec_graph(self) -> Graph:
        return self._scenario_exec_graph

    def load_behaviour_impl(
        self, context: Context, bhv_id: URIRef, override: bool = False, **kwargs: Any
    ) -> BehaviourImplModel:
        if bhv_id in self._bhv_impl and not override:
            return self._bhv_impl[bhv_id]

        bhv_impl_ids = list(
            self._scenario_exec_graph.subjects(object=bhv_id, predicate=URI_BHV_PRED_OF_BHV)
        )
        assert (
            len(bhv_impl_ids) == 1
        ), f"not exactly 1 implementation found for '{bhv_id}', found: {bhv_impl_ids}"
        assert isinstance(bhv_impl_ids[0], URIRef)

        assert hasattr(context, "model_graph"), "'model_graph' not added to behave context"

        bhv_impl = BehaviourImplModel(graph=context.model_graph, bhv_impl_uri=bhv_impl_ids[0])
        self.bhv_model_loader.load_attributes(graph=context.model_graph, model=bhv_impl)

        if URI_PY_TYPE_MODULE_ATTR in bhv_impl.types:
            bhv_cls = import_attr_from_model(model=bhv_impl)
            assert issubclass(
                bhv_cls, Behaviour
            ), f"Implementation for '{bhv_impl.id}' is not an extension of '{Behaviour}'"
            bhv_impl.behaviour = bhv_cls(context=context, **kwargs)

        assert bhv_impl.behaviour is not None

        self._bhv_impl[bhv_id] = bhv_impl
        return bhv_impl
