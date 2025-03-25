# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Any, Optional, Generator
from rdflib import Graph, URIRef
from rdflib.exceptions import UniquenessError
from rdf_utils.models.common import AttrLoaderProtocol, ModelBase, ModelLoader, get_node_types
from bdd_dsl.models.queries import Q_MODELLED_OBJECT
from bdd_dsl.models.urirefs import (
    URI_ENV_PRED_HAS_OBJ,
    URI_ENV_PRED_HAS_OBJ_MODEL,
    URI_ENV_PRED_HAS_WS,
    URI_ENV_PRED_OF_WS,
    URI_ENV_TYPE_WS_OBJ,
    URI_ENV_TYPE_WS_WS,
)
from bdd_dsl.simulation.common import load_attr_has_config


class ObjectModel(ModelBase):
    models: dict[URIRef, ModelBase]
    model_types: set[URIRef]
    model_type_to_id: dict[URIRef, set[URIRef]]  # map a model type to a set of model URIs

    def __init__(self, graph: Graph, obj_id: URIRef):
        super().__init__(graph=graph, node_id=obj_id)
        self.models = {}
        self.model_types = set()
        self.model_type_to_id = {}

        load_attr_has_config(graph=graph, model=self)

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

        assert len(self.model_types) > 0, f"obj '{obj_id}' has no model type"

    def load_model_attrs(self, graph: Graph, model_loader: ModelLoader, **kwargs: Any) -> None:
        for model in self.models.values():
            model_loader.load_attributes(graph=graph, model=model, **kwargs)

    def load_first_model_by_type(self, model_type: URIRef) -> ModelBase:
        for model_uri in self.model_type_to_id[model_type]:
            return self.models[model_uri]

        raise RuntimeError(f"object '{self.id}' doesn't have a model of type '{model_type}'")


class WorkspaceModel(ModelBase):
    workspaces: set[URIRef]
    objects: set[URIRef]

    def __init__(self, ws_id: URIRef, graph) -> None:
        super().__init__(node_id=ws_id, graph=graph)
        self.workspaces = set()
        self.objects = set()


def _get_ws_objects_re(
    ws_id: URIRef, ws_dict: dict[URIRef, WorkspaceModel], ws_path: Optional[set[URIRef]] = None
) -> Generator[URIRef, None, None]:
    if ws_path is None:
        ws_path = set()
    if ws_id in ws_path:
        raise RuntimeError(f"_get_ws_objects_re: loop detected at {ws_id}")
    ws_path.add(ws_id)

    assert ws_id in ws_dict, f"_get_ws_objects_re: '{ws_id}' not on record"
    ws_model = ws_dict[ws_id]
    for sub_ws_id in ws_model.workspaces:
        assert (
            sub_ws_id in ws_dict
        ), f"sub-ws '{sub_ws_id}' of workspace '{ws_model.id}' not on record"
        for obj_id in _get_ws_objects_re(ws_id=sub_ws_id, ws_dict=ws_dict, ws_path=ws_path):
            yield obj_id

    for obj_id in ws_model.objects:
        yield obj_id


def _load_ws_re(
    ws_id: URIRef,
    graph: Graph,
    ws_dict: dict[URIRef, WorkspaceModel],
    ws_path: Optional[set[URIRef]] = None,
) -> None:
    if ws_path is None:
        ws_path = set()
    assert ws_id not in ws_path, f"_load_ws_re: loop detected at '{ws_id}'"
    ws_path.add(ws_id)

    if ws_id in ws_dict:
        # assuming this subtree of workspaces is already loaded
        return

    ws_model = WorkspaceModel(ws_id=ws_id, graph=graph)
    ws_dict[ws_id] = ws_model
    try:
        ws_comp_id = graph.value(object=ws_id, predicate=URI_ENV_PRED_OF_WS, any=False)
    except UniquenessError as e:
        raise RuntimeError(f"multiple composition for workspace '{ws_id}': {e}")
    assert isinstance(
        ws_comp_id, URIRef
    ), f"no ref to composition URI for ws '{ws_id}': {ws_comp_id}"

    ws_comp_types = get_node_types(node_id=ws_comp_id, graph=graph)

    if URI_ENV_TYPE_WS_OBJ in ws_comp_types:
        for obj_id in graph.objects(subject=ws_comp_id, predicate=URI_ENV_PRED_HAS_OBJ):
            assert isinstance(
                obj_id, URIRef
            ), f"comp '{ws_comp_id}' of ws '{ws_id}' does not ref an obj URI: {obj_id}"
            ws_model.objects.add(obj_id)

    if URI_ENV_TYPE_WS_WS in ws_comp_types:
        for sub_ws_id in graph.objects(subject=ws_comp_id, predicate=URI_ENV_PRED_HAS_WS):
            assert isinstance(
                sub_ws_id, URIRef
            ), f"'{ws_comp_id}' of ws '{ws_id}' does not ref a ws URI: {sub_ws_id}"

            ws_model.workspaces.add(sub_ws_id)
            _load_ws_re(ws_id=sub_ws_id, graph=graph, ws_dict=ws_dict, ws_path=ws_path)


class EnvModelLoader(object):
    _model_loader: ModelLoader
    _modelled_obj_g: Optional[Graph]
    _obj_models: dict[URIRef, ObjectModel]
    _ws_models: dict[URIRef, WorkspaceModel]

    def __init__(self):
        self._modelled_obj_g = None
        self._model_loader = ModelLoader()
        self._obj_models = {}  # Object URI -> ObjectModel instance
        self._ws_models = {}  # Workspace URI -> WorkspaceModel instance

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

    def load_ws_model(
        self, graph: Graph, ws_id: URIRef, override: bool = False, **kwargs: Any
    ) -> WorkspaceModel:
        if ws_id in self._ws_models and not override:
            return self._ws_models[ws_id]

        _load_ws_re(ws_id=ws_id, graph=graph, ws_dict=self._ws_models)

        for obj_id in _get_ws_objects_re(ws_id=ws_id, ws_dict=self._ws_models):
            _ = self.load_object_model(graph=graph, obj_id=obj_id, override=override, **kwargs)

        assert ws_id in self._ws_models, f"_load_ws_re did not add '{ws_id}' to EnvModelLoader"
        return self._ws_models[ws_id]

    def load_ws_objects(
        self, graph: Graph, ws_id: URIRef, override: bool = False, **kwargs: Any
    ) -> Generator[ObjectModel, None, None]:
        if ws_id not in self._ws_models:
            _ = self.load_ws_model(graph=graph, ws_id=ws_id, override=override, **kwargs)

        for obj_id in _get_ws_objects_re(ws_id=ws_id, ws_dict=self._ws_models):
            assert obj_id in self._obj_models, f"obj '{obj_id}' not loaded for ws {ws_id}"
            yield self._obj_models[obj_id]

    def register_attr_loaders(self, *loaders: AttrLoaderProtocol) -> None:
        for ldr in loaders:
            self._model_loader.register(loader=ldr)
