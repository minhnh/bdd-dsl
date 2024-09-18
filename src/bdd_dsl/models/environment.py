# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Dict
from rdflib import Graph, URIRef
from rdf_utils.models import ModelBase
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
