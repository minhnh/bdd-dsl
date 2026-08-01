# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Any

from behave.runner import Context
from rdf_utils.models.common import AttrLoaderProtocol, ModelBase
from rdf_utils.models.python import (
    URI_PY_TYPE_MODULE_ATTR,
    import_attr_from_model,
)
from rdf_utils.models.vocab import URI_EXEC_PRED_RUNS_SCENE, URI_EXEC_TYPE_SCENE_INST
from rdflib import RDF, Graph, URIRef

from bdd_dsl.execution.behaviour import Behaviour, BehaviourImplModel
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
    scene_inst_id: URIRef

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

        scene_inst_ids = list(graph.objects(self.id, URI_EXEC_PRED_RUNS_SCENE))
        if len(scene_inst_ids) != 1 or not isinstance(scene_inst_ids[0], URIRef):
            raise ValueError(
                f"ScenarioExecution '{self.id}' must run exactly 1 scene instance: {scene_inst_ids}"
            )
        self.scene_inst_id = scene_inst_ids[0]
        if (self.scene_inst_id, RDF.type, URI_EXEC_TYPE_SCENE_INST) not in graph:
            raise TypeError(
                f"ScenarioExecution '{self.id}' runs non-SceneInstance '{self.scene_inst_id}'"
            )

        # Boundary events
        dur = get_duration(scr_var.tmpl)
        start_evt = dur.get(URI_TIME_PRED_AFTER_EVT)
        end_evt = dur.get(URI_TIME_PRED_BEFORE_EVT)
        if start_evt is None or end_evt is None:
            raise ValueError(
                f"ScenarioVariant '{scr_var.id.n3(graph.namespace_manager)}'"
                f" has invalid start/end events: start={start_evt}, end={end_evt}"
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
            raise TypeError(
                f"ScenarioExecution '{self.id}' doesn't link to a BehaviourImplementation URI: {bhv_impl_id}"
            )
        self.bhv_impl = BehaviourImplModel(graph=graph, bhv_impl_id=bhv_impl_id)
        for loader in bhv_loaders:
            loader(graph=graph, model=self.bhv_impl)

        # Observation policies
        self.obs_policy_uris = set()
        for obs_pol_id in graph.objects(subject=self.id, predicate=URI_OBS_PRED_POLICY):
            if not isinstance(obs_pol_id, URIRef):
                raise TypeError(
                    f"ScenarioExecution {self.id} doesn't link to an ObservationPolicy URI: {obs_pol_id}"
                )
            self.obs_policy_uris.add(obs_pol_id)

    def load_behaviour_impl(self, context: Context, **kwargs: Any) -> BehaviourImplModel:
        if self.bhv_impl.behaviour is not None:
            return self.bhv_impl

        if URI_PY_TYPE_MODULE_ATTR in self.bhv_impl.types:
            bhv_cls = import_attr_from_model(model=self.bhv_impl)
            assert issubclass(bhv_cls, Behaviour), (
                f"Implementation for '{self.bhv_impl.id}' is not an extension of '{Behaviour}'"
            )
            self.bhv_impl.behaviour = bhv_cls(
                bhv_id=self.bhv_impl.behaviour_uri,
                bhv_types=self.bhv_impl.behaviour_types,
                context=context,
                **kwargs,
            )

        assert self.bhv_impl.behaviour is not None, (
            f"no behaviour type handled for BehaviourImpl '{self.bhv_impl.id}', "
            f"types: {self.bhv_impl.types}"
        )
        return self.bhv_impl
