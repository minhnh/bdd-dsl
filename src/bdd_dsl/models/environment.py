# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Dict, Any
from rdflib import Graph, URIRef
from rdf_utils.models import ModelBase, ModelLoader
from bdd_dsl.models.queries import Q_SIMULATED_OBJECT
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
            assert isinstance(model_id, URIRef)

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


class ObjModelLoader(object):
    model_loader: ModelLoader
    _sim_obj_graph: Graph
    _obj_models: Dict[URIRef, ObjectModel]

    def __init__(self, graph: Graph):
        q_result = graph.query(Q_SIMULATED_OBJECT)
        assert (
            q_result.type == "CONSTRUCT" and q_result.graph is not None
        ), "querying simulated objects failed"

        self._sim_obj_graph = q_result.graph
        self._obj_models = {}  # Object URI -> ObjectModel instance

        self.model_loader = ModelLoader()

    def load_object_model(
        self, graph: Graph, obj_id: URIRef, override: bool = False, **kwargs: Any
    ) -> ObjectModel:
        if obj_id in self._obj_models and not override:
            return self._obj_models[obj_id]

        obj_model = ObjectModel(graph=self._sim_obj_graph, obj_id=obj_id)
        self.model_loader.load_attributes(graph=graph, model=obj_model, **kwargs)
        self._obj_models[obj_id] = obj_model
        return obj_model
