# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Any, Dict, Optional
from rdflib import Graph, URIRef
from rdf_utils.models import AttrLoaderProtocol, ModelBase, ModelLoader
from bdd_dsl.models.queries import Q_MODELLED_AGENT
from bdd_dsl.models.urirefs import URI_AGN_PRED_HAS_AGN_MODEL


class AgentModel(ModelBase):
    models: Dict[URIRef, ModelBase]
    model_types: set[URIRef]
    model_type_to_id: Dict[URIRef, set[URIRef]]  # map a model type to a set of model URIs

    def __init__(self, graph: Graph, agent_id: URIRef) -> None:
        super().__init__(graph=graph, node_id=agent_id)
        self.models = {}
        self.model_types = set()
        self.model_type_to_id = {}

        for model_id in graph.objects(subject=agent_id, predicate=URI_AGN_PRED_HAS_AGN_MODEL):
            assert isinstance(model_id, URIRef)

            agn_model = ModelBase(graph=graph, node_id=model_id)
            assert (
                agn_model.id not in self.models
            ), f"Agent '{self.id}' has duplicate models '{agn_model.id}'"
            self.models[agn_model.id] = agn_model

            for model_type in agn_model.types:
                self.model_types.add(model_type)
                if model_type not in self.model_type_to_id:
                    self.model_type_to_id[model_type] = set()

                self.model_type_to_id[model_type].add(agn_model.id)

    def load_model_attrs(self, graph: Graph, model_loader: ModelLoader, **kwargs: Any) -> None:
        for model in self.models.values():
            model_loader.load_attributes(graph=graph, model=model, **kwargs)

    def load_first_model_by_type(self, model_type: URIRef) -> ModelBase:
        for model_uri in self.model_type_to_id[model_type]:
            return self.models[model_uri]

        raise RuntimeError(f"object '{self.id}' doesn't have a model of type '{model_type}'")


class AgnModelLoader(object):
    _model_loader: ModelLoader
    _modelled_agn_g: Optional[Graph]
    _agn_models: Dict[URIRef, AgentModel]

    def __init__(self):
        self._agn_models = {}  # Agent URI -> AgentModel instance
        self._modelled_agn_g = None
        self._model_loader = ModelLoader()

    def _query_agent_models(self, graph: Graph) -> Graph:
        q_result = graph.query(Q_MODELLED_AGENT)
        assert (
            q_result.type == "CONSTRUCT" and q_result.graph is not None
        ), "querying for ModelledAgent's failed"
        assert len(q_result.graph) > 0, "querying for ModelledAgent's returned an empty graph"

        return q_result.graph

    def load_agent_model(
        self, graph: Graph, agent_id: URIRef, override: bool = False, **kwargs: Any
    ) -> AgentModel:
        if agent_id in self._agn_models and not override:
            return self._agn_models[agent_id]

        if self._modelled_agn_g is None:
            self._modelled_agn_g = self._query_agent_models(graph=graph)

        agn_model = AgentModel(graph=self._modelled_agn_g, agent_id=agent_id)
        agn_model.load_model_attrs(graph=graph, model_loader=self._model_loader, **kwargs)
        self._agn_models[agent_id] = agn_model
        return agn_model

    def register_attr_loaders(self, *loaders: AttrLoaderProtocol) -> None:
        for ldr in loaders:
            self._model_loader.register(loader=ldr)
