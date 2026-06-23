# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Any
from behave.runner import Context
from rdf_utils.models.common import AttrLoaderProtocol, ModelBase, ModelLoader
from rdflib import Graph, URIRef
from rdf_utils.caching import read_url_and_cache
from rdf_utils.models.python import (
    URI_PY_TYPE_MODULE_ATTR,
    import_attr_from_model,
    load_py_module_attr,
)
from bdd_dsl.execution.behaviour import Behaviour, BehaviourImplModel
from bdd_dsl.execution.common import URL_Q_SCENARIO_EXEC
from bdd_dsl.models.time_constraint import get_duration
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_HAS_BHV_IMPL,
    URI_BDD_PRED_OF_VARIANT,
    URI_BDD_TYPE_SCENARIO_EXEC,
    URI_OBS_PRED_POLICY,
    URI_TIME_PRED_AFTER_EVT,
    URI_TIME_PRED_BEFORE_EVT,
)
from bdd_dsl.models.user_story import (
    ScenarioVariantModel,
)


class ScenarioExecutionModel(ModelBase):
    variant_id: URIRef
    start_event: URIRef
    end_event: URIRef
    bhv_impl: BehaviourImplModel
    obs_policy_uris: set[URIRef]

    def __init__(
        self,
        graph: Graph,
        scr_var: ScenarioVariantModel,
        bhv_loaders: list[AttrLoaderProtocol],
    ) -> None:
        self.variant_id = scr_var.id
        scr_exec_ids = list(
            graph.subjects(predicate=URI_BDD_PRED_OF_VARIANT, object=self.variant_id)
        )
        if len(scr_exec_ids) != 1 or not isinstance(scr_exec_ids[0], URIRef):
            raise ValueError(
                f"ScenarioVariant '{self.variant_id}' does not link to exactly 1 execution model URI: {scr_exec_ids}"
            )

        super().__init__(graph=graph, node_id=scr_exec_ids[0])
        if URI_BDD_TYPE_SCENARIO_EXEC not in self.types:
            raise ValueError(f"'{self.id}' missing expected ScenarioExecution type: {self.types}")

        # Boundary events
        dur = get_duration(scr_var.tmpl)
        start_evt = dur.get(URI_TIME_PRED_AFTER_EVT)
        end_evt = dur.get(URI_TIME_PRED_BEFORE_EVT)
        if start_evt is None or end_evt is None:
            raise ValueError(
                f"ScenarioVariant '{scr_var.id.n3(graph.namespace_manager)}'"
                f" has invalid start/end events: start={self.start_event}, end={self.end_event}"
            )
        if start_evt == end_evt:
            raise ValueError(
                f"ScenarioVariant '{scr_var.id.n3(graph.namespace_manager)}'"
                f" has same start/end events: {start_evt}"
            )
        self.start_event = start_evt
        self.end_event = end_evt

        # Behaviour Implementation model
        bhv_impl_id = graph.value(subject=self.id, predicate=URI_BDD_PRED_HAS_BHV_IMPL, any=False)
        if not isinstance(bhv_impl_id, URIRef):
            raise ValueError(
                f"ScenarioExecution '{self.id}' doesn't link to a BehaviourImplementation URI: {bhv_impl_id}"
            )
        self.bhv_impl = BehaviourImplModel(graph=graph, bhv_impl_id=bhv_impl_id)
        for loader in bhv_loaders:
            loader(graph=graph, model=self.bhv_impl)

        # Observation policies
        self.obs_policy_uris = set()
        for obs_pol_id in graph.objects(subject=self.id, predicate=URI_OBS_PRED_POLICY):
            if not isinstance(obs_pol_id, URIRef):
                raise ValueError(
                    f"ScenarioExecution {self.id} doesn't link to an ObservationPolicy URI: {obs_pol_id}"
                )
            self.obs_policy_uris.add(obs_pol_id)


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
        assert q_result.type == "CONSTRUCT" and q_result.graph is not None, (
            "ScenarioExecution query did not return a graph"
        )
        assert len(q_result.graph) > 0, "ScenarioExecution query returns an empty graph"
        self._scr_exec_graph = q_result.graph

        self._bhv_impl_by_scr_var = {}
        self._scr_exec_by_scr_var = {}

        self.bhv_model_loader = ModelLoader()
        for loader in bhv_loaders:
            self.bhv_model_loader.register(loader=loader)

    def load_behaviour_impl(self, context: Context, **kwargs: Any) -> BehaviourImplModel:
        assert hasattr(context, "model_graph"), "'model_graph' not added to behave context"
        assert isinstance(context.model_graph, Graph), (
            "load_bhv_impl: 'model_graph' not a rdflib.Graph"
        )
        assert hasattr(context, "current_scenario"), (
            "'current_scenario' not added to behave context"
        )
        assert isinstance(context.current_scenario, ScenarioVariantModel), (
            "load_bhv_impl: 'model_graph' not a rdflib.Graph"
        )

        scr_var_id = context.current_scenario.id
        if scr_var_id in self._bhv_impl_by_scr_var:
            return self._bhv_impl_by_scr_var[scr_var_id]

        scr_exec_id = self._scr_exec_graph.value(
            predicate=URI_BDD_PRED_OF_VARIANT, object=scr_var_id, any=False
        )
        assert isinstance(scr_exec_id, URIRef), (
            f"'{scr_var_id}' doesn't link to a ScenarioExecution URI: {scr_exec_id}"
        )
        scr_exec_model = ModelBase(node_id=scr_exec_id, graph=self._scr_exec_graph)
        self._scr_exec_by_scr_var[scr_var_id] = scr_exec_model

        bhv_impl_id = self._scr_exec_graph.value(
            subject=scr_exec_id, predicate=URI_BDD_PRED_HAS_BHV_IMPL, any=False
        )
        assert isinstance(bhv_impl_id, URIRef), (
            f"ScenarioExecution '{scr_exec_id}' doesn't link to a BehaviourImplementation URI: {bhv_impl_id}"
        )
        bhv_impl = BehaviourImplModel(graph=self._scr_exec_graph, bhv_impl_id=bhv_impl_id)

        self.bhv_model_loader.load_attributes(graph=context.model_graph, model=bhv_impl)

        if URI_PY_TYPE_MODULE_ATTR in bhv_impl.types:
            bhv_cls = import_attr_from_model(model=bhv_impl)
            assert issubclass(bhv_cls, Behaviour), (
                f"Implementation for '{bhv_impl.id}' is not an extension of '{Behaviour}'"
            )
            bhv_impl.behaviour = bhv_cls(
                bhv_id=bhv_impl.behaviour_uri,
                bhv_types=bhv_impl.behaviour_types,
                context=context,
                **kwargs,
            )

        assert bhv_impl.behaviour is not None, (
            f"no behaviour type handled for BehaviourImpl '{bhv_impl.id}', types: {bhv_impl.types}"
        )

        self._bhv_impl_by_scr_var[scr_var_id] = bhv_impl
        return bhv_impl
