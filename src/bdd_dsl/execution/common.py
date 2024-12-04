# SPDX-License-Identifier:  GPL-3.0-or-later
from abc import ABC, abstractmethod
from typing import Any, Optional
from behave.runner import Context
from rdf_utils.models.common import AttrLoaderProtocol, ModelBase, ModelLoader, get_node_types
from rdflib import Graph, URIRef
from rdf_utils.uri import URL_SECORO_M
from rdf_utils.caching import read_url_and_cache
from rdf_utils.models.python import (
    URI_PY_TYPE_MODULE_ATTR,
    import_attr_from_model,
    load_py_module_attr,
)
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_OF_VARIANT,
    URI_BHV_PRED_OF_BHV,
    URI_BDD_PRED_HAS_BHV_IMPL,
)
from bdd_dsl.models.user_story import ScenarioVariantModel


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
    behaviour_uri: URIRef
    behaviour_types: set[URIRef]

    def __init__(self, graph: Graph, bhv_impl_id: URIRef) -> None:
        super().__init__(graph=graph, node_id=bhv_impl_id)
        self.behaviour = None

        bhv_uri = graph.value(subject=self.id, predicate=URI_BHV_PRED_OF_BHV)
        assert isinstance(
            bhv_uri, URIRef
        ), f"BehaviourImpl '{self.id}' doesnn't ref a Behaviour URI: {bhv_uri}"
        self.behaviour_uri = bhv_uri

        self.behaviour_types = get_node_types(graph=graph, node_id=self.behaviour_uri)
        assert len(self.behaviour_types) > 0, f"No types found for Behaviour '{self.behaviour_uri}'"


class ExecutionModel(object):
    _bhv_impl_by_scr_var: dict[URIRef, BehaviourImplModel]
    _scr_exec_by_scr_var: dict[URIRef, ModelBase]
    _scr_exec_graph: Graph
    bhv_model_loader: ModelLoader

    def __init__(
        self, graph: Graph, bhv_loaders: list[AttrLoaderProtocol] = [load_py_module_attr]
    ) -> None:
        g_query_str = read_url_and_cache(URL_Q_SCENARIO_EXEC)
        q_result = graph.query(g_query_str)
        assert (
            q_result.type == "CONSTRUCT" and q_result.graph is not None
        ), "ScenarioExecution query did not return a graph"
        assert len(q_result.graph) > 0, "ScenarioExecution query returns an empty graph"
        self._scr_exec_graph = q_result.graph

        self._bhv_impl_by_scr_var = {}
        self._scr_exec_by_scr_var = {}

        self.bhv_model_loader = ModelLoader()
        for loader in bhv_loaders:
            self.bhv_model_loader.register(loader=loader)

    def load_behaviour_impl(self, context: Context, **kwargs: Any) -> BehaviourImplModel:
        assert hasattr(context, "model_graph"), "'model_graph' not added to behave context"
        assert isinstance(
            context.model_graph, Graph
        ), "load_bhv_impl: 'model_graph' not a rdflib.Graph"
        assert hasattr(
            context, "current_scenario"
        ), "'current_scenario' not added to behave context"
        assert isinstance(
            context.current_scenario, ScenarioVariantModel
        ), "load_bhv_impl: 'model_graph' not a rdflib.Graph"

        scr_var_id = context.current_scenario.id
        if scr_var_id in self._bhv_impl_by_scr_var:
            return self._bhv_impl_by_scr_var[scr_var_id]

        scr_exec_id = self._scr_exec_graph.value(
            predicate=URI_BDD_PRED_OF_VARIANT, object=scr_var_id, any=False
        )
        assert isinstance(
            scr_exec_id, URIRef
        ), f"'{scr_var_id}' doesn't link to a ScenarioExecution URI: {scr_exec_id}"
        scr_exec_model = ModelBase(node_id=scr_exec_id, graph=self._scr_exec_graph)
        self._scr_exec_by_scr_var[scr_var_id] = scr_exec_model

        bhv_impl_id = self._scr_exec_graph.value(
            subject=scr_exec_id, predicate=URI_BDD_PRED_HAS_BHV_IMPL, any=False
        )
        assert isinstance(
            bhv_impl_id, URIRef
        ), f"ScenarioExecution '{scr_exec_id}' doesn't link to a BehaviourImplementation URI: {bhv_impl_id}"
        bhv_impl = BehaviourImplModel(graph=self._scr_exec_graph, bhv_impl_id=bhv_impl_id)

        self.bhv_model_loader.load_attributes(graph=context.model_graph, model=bhv_impl)

        if URI_PY_TYPE_MODULE_ATTR in bhv_impl.types:
            bhv_cls = import_attr_from_model(model=bhv_impl)
            assert issubclass(
                bhv_cls, Behaviour
            ), f"Implementation for '{bhv_impl.id}' is not an extension of '{Behaviour}'"
            bhv_impl.behaviour = bhv_cls(context=context, **kwargs)

        assert (
            bhv_impl.behaviour is not None
        ), f"no behaviour type handled for BehaviourImpl '{bhv_impl.id}', types: {bhv_impl.types}"

        self._bhv_impl_by_scr_var[scr_var_id] = bhv_impl
        return bhv_impl
