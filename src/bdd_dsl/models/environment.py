# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Dict, Any, Optional
from rdflib import Graph, URIRef
from rdf_utils.models.common import AttrLoaderProtocol, ModelBase, ModelLoader
from bdd_dsl.models.queries import Q_MODELLED_OBJECT
from bdd_dsl.models.urirefs import URI_ENV_PRED_HAS_OBJ_MODEL


class ObjectModel(ModelBase):
    models: Dict[URIRef, ModelBase]
    model_types: set[URIRef]
    model_type_to_id: Dict[URIRef, set[URIRef]]  # map a model type to a set of model URIs

    def __init__(self, graph: Graph, obj_id: URIRef):
        super().__init__(graph=graph, node_id=obj_id)
        self.models = {}
        self.model_types = set()
        self.model_type_to_id = {}

        for model_id in graph.objects(subject=obj_id, predicate=URI_ENV_PRED_HAS_OBJ_MODEL):
            assert isinstance(
                model_id, URIRef
            ), f"unexpected type for model ID (not URIRef): {type(model_id)}"

            obj_model = ModelBase(graph=graph, node_id=model_id)
            assert (
                obj_model.id not in self.models
            ), f"Obj '{self.id}' has duplicate models '{obj_model.id}'"
            self.models[obj_model.id] = obj_model

            for model_type in obj_model.types:
                self.model_types.add(model_type)
                if model_type not in self.model_type_to_id:
                    self.model_type_to_id[model_type] = set()

                self.model_type_to_id[model_type].add(obj_model.id)

    def load_model_attrs(self, graph: Graph, model_loader: ModelLoader, **kwargs: Any) -> None:
        for model in self.models.values():
            model_loader.load_attributes(graph=graph, model=model, **kwargs)

    def load_first_model_by_type(self, model_type: URIRef) -> ModelBase:
        for model_uri in self.model_type_to_id[model_type]:
            return self.models[model_uri]

        raise RuntimeError(f"object '{self.id}' doesn't have a model of type '{model_type}'")


class ObjModelLoader(object):
    _model_loader: ModelLoader
    _modelled_obj_g: Optional[Graph]
    _obj_models: Dict[URIRef, ObjectModel]

    def __init__(self):
        self._modelled_obj_g = None
        self._model_loader = ModelLoader()
        self._obj_models = {}  # Object URI -> ObjectModel instance

    def _query_obj_models(self, graph: Graph) -> Graph:
        q_result = graph.query(Q_MODELLED_OBJECT)
        assert (
            q_result.type == "CONSTRUCT" and q_result.graph is not None
        ), "querying ModelledObject's failed"
        assert len(q_result.graph) > 0, "querying for ModelledObject's returned an empty graph"

        return q_result.graph

    def load_object_model(
        self, graph: Graph, obj_id: URIRef, override: bool = False, **kwargs: Any
    ) -> ObjectModel:
        if obj_id in self._obj_models and not override:
            return self._obj_models[obj_id]

        if self._modelled_obj_g is None:
            self._modelled_obj_g = self._query_obj_models(graph=graph)

        obj_model = ObjectModel(graph=self._modelled_obj_g, obj_id=obj_id)
        obj_model.load_model_attrs(graph=graph, model_loader=self._model_loader, **kwargs)
        self._obj_models[obj_id] = obj_model
        return obj_model

    def register_attr_loaders(self, *loaders: AttrLoaderProtocol) -> None:
        for ldr in loaders:
            self._model_loader.register(loader=ldr)
