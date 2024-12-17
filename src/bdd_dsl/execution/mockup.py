# SPDX-License-Identifier:  GPL-3.0-or-later
from time import sleep
from typing import Any, Optional
from behave.runner import Context
from behave.model import Scenario
from rdflib import Graph
from rdf_utils.models.common import ModelLoader, URIRef
from rdf_utils.models.python import (
    URI_PY_TYPE_MODULE_ATTR,
    URI_PY_PRED_ATTR_NAME,
    URI_PY_PRED_MODULE_NAME,
    load_py_module_attr,
)
from rdf_utils.uri import NamespaceManager, try_expand_curie
from bdd_dsl.behave import (
    PARAM_AGN,
    PARAM_EVT,
    PARAM_OBJ,
    PARAM_WS,
    load_obj_models_from_table,
    load_agn_models_from_table,
    load_str_params,
    load_ws_models_from_table,
    parse_str_param,
)
from bdd_dsl.execution.common import Behaviour, ExecutionModel
from bdd_dsl.models.urirefs import URI_SIM_PRED_PATH, URI_SIM_TYPE_RES_PATH
from bdd_dsl.simulation.common import load_attr_has_config, load_attr_path
from bdd_dsl.models.user_story import ScenarioVariantModel, UserStoryLoader


def before_all_mockup(context: Context):
    g = getattr(context, "model_graph", None)
    assert g is not None, "'model_graph' attribute not found in context"

    exec_model = ExecutionModel(graph=g)
    context.execution_model = exec_model
    context.us_loader = UserStoryLoader(graph=g)

    generic_loader = ModelLoader()
    context.ws_model_loader = generic_loader


def before_scenario(context: Context, scenario: Scenario):
    model_graph = getattr(context, "model_graph", None)
    assert model_graph is not None

    us_loader = getattr(context, "us_loader", None)
    assert us_loader is not None and isinstance(us_loader, UserStoryLoader)

    # scenario outline renders each scenario as
    #   SCHEMA: "{outline_name} -- {examples.name}@{row.id}"
    scr_name_splits = scenario.name.split(" -- ")
    assert len(scr_name_splits) > 0, f"unexpected scenario name: {scenario.name}"
    scr_name = scr_name_splits[0]
    scenario_var_uri = try_expand_curie(
        curie_str=scr_name, ns_manager=model_graph.namespace_manager, quiet=False
    )
    assert scenario_var_uri is not None, f"can't parse '{scr_name}' as URI"

    scenario_var_model = us_loader.load_scenario_variant(
        full_graph=model_graph, variant_id=scenario_var_uri
    )
    assert isinstance(scenario_var_model, ScenarioVariantModel)
    assert (
        len(scenario_var_model.scene.objects) > 0
    ), f"scene '{scenario_var_model.scene.id}' has no object"
    assert (
        len(scenario_var_model.scene.workspaces) > 0
    ), f"scene '{scenario_var_model.scene.id}' has no workspace"
    assert (
        len(scenario_var_model.scene.agents) > 0
    ), f"scene '{scenario_var_model.scene.id}' has no agent"

    scenario_var_model.scene.env_model_loader.register_attr_loaders(
        load_attr_path, load_attr_has_config, load_py_module_attr
    )
    scenario_var_model.scene.agn_model_loader.register_attr_loaders(load_py_module_attr)
    context.current_scenario = scenario_var_model


def given_objects_mockup(context: Context):
    assert context.table is not None, "no table added to context, expected a list of object URIs"
    assert context.model_graph is not None, "no 'model_graph' in context, expected an rdflib.Graph"
    assert (
        context.current_scenario is not None
    ), "no 'current_scenario' in context, expected a ScenarioVariantModel"
    for obj_model in load_obj_models_from_table(
        table=context.table, graph=context.model_graph, scene=context.current_scenario.scene
    ):
        if URI_PY_TYPE_MODULE_ATTR in obj_model.model_types:
            for py_model_uri in obj_model.model_type_to_id[URI_PY_TYPE_MODULE_ATTR]:
                py_model = obj_model.models[py_model_uri]
                assert py_model.has_attr(
                    key=URI_PY_PRED_MODULE_NAME
                ), f"Python attribute model '{py_model.id}' for object '{obj_model.id}' missing module name"
                assert py_model.has_attr(
                    key=URI_PY_PRED_ATTR_NAME
                ), f"Python attribute model '{py_model.id}' for object '{obj_model.id}' missing attribute name"

        if URI_SIM_TYPE_RES_PATH in obj_model.model_types:
            for py_model_uri in obj_model.model_type_to_id[URI_SIM_TYPE_RES_PATH]:
                path_model = obj_model.load_first_model_by_type(model_type=URI_SIM_TYPE_RES_PATH)
                assert path_model.has_attr(
                    URI_SIM_PRED_PATH
                ), f"ResourceWithPath model '{path_model.id}' for object '{obj_model.id}' missing attr path"


def given_workspaces_mockup(context: Context):
    assert context.table is not None, "no table added to context, expected a list of object URIs"
    assert context.model_graph is not None, "no 'model_graph' in context, expected an rdflib.Graph"
    assert (
        context.current_scenario is not None
    ), "no 'current_scenario' in context, expected a ScenarioVariantModel"
    for ws_model in load_ws_models_from_table(
        table=context.table, graph=context.model_graph, scene=context.current_scenario.scene
    ):
        env_loader = context.current_scenario.scene.env_model_loader
        for obj_model in env_loader.load_ws_objects(graph=context.model_graph, ws_id=ws_model.id):
            if URI_PY_TYPE_MODULE_ATTR in obj_model.model_types:
                for py_model_uri in obj_model.model_type_to_id[URI_PY_TYPE_MODULE_ATTR]:
                    py_model = obj_model.models[py_model_uri]
                    assert py_model.has_attr(
                        key=URI_PY_PRED_MODULE_NAME
                    ), f"Python attribute model '{py_model.id}' for object '{obj_model.id}' missing module name"
                    assert py_model.has_attr(
                        key=URI_PY_PRED_ATTR_NAME
                    ), f"Python attribute model '{py_model.id}' for object '{obj_model.id}' missing attribute name"

            if URI_SIM_TYPE_RES_PATH in obj_model.model_types:
                for py_model_uri in obj_model.model_type_to_id[URI_SIM_TYPE_RES_PATH]:
                    path_model = obj_model.load_first_model_by_type(
                        model_type=URI_SIM_TYPE_RES_PATH
                    )
                    assert path_model.has_attr(
                        URI_SIM_PRED_PATH
                    ), f"ResourceWithPath model '{path_model.id}' for object '{obj_model.id}' missing attr path"


def given_agents_mockup(context: Context):
    assert context.table is not None, "no table added to context, expected a list of agent URIs"
    assert context.model_graph is not None, "no 'model_graph' in context, expected an rdflib.Graph"
    assert (
        context.current_scenario is not None
    ), "no 'current_scenario' in context, expected an ScenarioVariantModel"
    for agn_model in load_agn_models_from_table(
        table=context.table, graph=context.model_graph, scene=context.current_scenario.scene
    ):
        if URI_PY_TYPE_MODULE_ATTR in agn_model.model_types:
            for py_model_uri in agn_model.model_type_to_id[URI_PY_TYPE_MODULE_ATTR]:
                py_model = agn_model.models[py_model_uri]
                assert py_model.has_attr(
                    key=URI_PY_PRED_MODULE_NAME
                ), f"Python attribute model '{py_model.id}' for agent '{agn_model.id}' missing module name"
                assert py_model.has_attr(
                    key=URI_PY_PRED_ATTR_NAME
                ), f"Python attribute model '{py_model.id}' for agent '{agn_model.id}' missing attribute name"


def given_scene_mockup(context: Context):
    pass


def is_located_at_mockup(context: Context, **kwargs: Any):
    params = load_str_params(param_names=[PARAM_OBJ, PARAM_WS, PARAM_EVT], **kwargs)

    assert context.model_graph is not None, "no 'model_graph' in context"
    assert (
        context.current_scenario is not None
    ), "no 'current_scenario' in context, expected an ScenarioVariantModel"

    _, pick_obj_uris = parse_str_param(
        param_str=params[PARAM_OBJ], ns_manager=context.model_graph.namespace_manager
    )
    for obj_uri in pick_obj_uris:
        obj_model = context.current_scenario.scene.load_obj_model(
            graph=context.model_graph, obj_id=obj_uri
        )
        assert obj_model is not None, f"can't load model for object {obj_uri}"
        if URI_PY_TYPE_MODULE_ATTR in obj_model.model_types:
            py_model = obj_model.load_first_model_by_type(URI_PY_TYPE_MODULE_ATTR)
            assert py_model.has_attr(
                key=URI_PY_PRED_MODULE_NAME
            ), f"Python attribute model '{py_model.id}' for object '{obj_model.id}' missing module name"
            assert py_model.has_attr(
                key=URI_PY_PRED_ATTR_NAME
            ), f"Python attribute model '{py_model.id}' for object '{obj_model.id}' missing attribute name"

    _, pick_ws_uris = parse_str_param(
        param_str=params[PARAM_WS], ns_manager=context.model_graph.namespace_manager
    )
    for ws_uri in pick_ws_uris:
        _ = context.current_scenario.scene.load_ws_model(graph=context.model_graph, ws_id=ws_uri)

    evt_uri = try_expand_curie(
        curie_str=params[PARAM_EVT], ns_manager=context.model_graph.namespace_manager, quiet=False
    )
    assert evt_uri is not None, f"can't parse '{params[PARAM_EVT]}' as URI"


def move_safe_mockup(context: Context, **kwargs: Any):
    assert context.model_graph is not None, "no 'model_graph' in context"
    assert (
        context.current_scenario is not None
    ), "no 'current_scenario' in context, expected an ScenarioVariantModel"

    params = load_str_params(param_names=[PARAM_AGN], **kwargs)
    _, pickplace_agn_uris = parse_str_param(
        param_str=params[PARAM_AGN], ns_manager=context.model_graph.namespace_manager
    )
    for agn_uri in pickplace_agn_uris:
        agn_model = context.current_scenario.scene.load_agn_model(
            graph=context.model_graph, agent_id=agn_uri
        )
        assert agn_model is not None, f"can't load model for agent {agn_uri}"


class PickplaceBehaviourMockup(Behaviour):
    agn_ids: Optional[list[URIRef]]
    obj_ids: Optional[list[URIRef]]
    place_ws_ids: Optional[list[URIRef]]

    def __init__(
        self,
        bhv_id: URIRef,
        bhv_types: set[URIRef],
        context: Any,
        ns_manager: NamespaceManager,
        **kwargs,
    ) -> None:
        super().__init__(bhv_id=bhv_id, bhv_types=bhv_types, context=context, **kwargs)

        self.max_count = kwargs.get("max_count", 5)
        self.counter = self.max_count

        self._ns_manager = ns_manager

        self.agn_ids = None
        self.obj_ids = None
        self.place_ws_ids = None

    def is_finished(self, context: Context, **kwargs: Any) -> bool:
        return self.counter <= 0

    def reset(self, context: Context, **kwargs: Any) -> None:
        self.counter = self.max_count

        agn_id_str = kwargs.get("agn_id_str", None)
        assert agn_id_str is not None, "arg 'agn_id_str' not specified'"
        obj_id_str = kwargs.get("obj_id_str", None)
        assert obj_id_str is not None, "arg 'obj_id_str' not specified'"
        ws_id_str = kwargs.get("ws_id_str", None)
        assert ws_id_str is not None, "arg 'ws_id_str not specified'"

        _, agn_uris = parse_str_param(param_str=agn_id_str, ns_manager=self._ns_manager)
        self.agn_ids = []
        for uri in agn_uris:
            assert isinstance(uri, URIRef), f"unexpected agent URI: {uri}"
            self.agn_ids.append(uri)

        _, obj_uris = parse_str_param(param_str=obj_id_str, ns_manager=self._ns_manager)
        self.obj_ids = []
        for uri in obj_uris:
            assert isinstance(uri, URIRef), f"unexpected obj URI: {uri}"
            self.obj_ids.append(uri)

        _, place_ws_uris = parse_str_param(param_str=ws_id_str, ns_manager=self._ns_manager)
        self.place_ws_ids = []
        for uri in place_ws_uris:
            assert isinstance(uri, URIRef), f"unexpected place ws URI: {uri}"
            self.place_ws_ids.append(uri)

    def step(self, context: Context, **kwargs: Any) -> Any:
        assert (
            self.agn_ids is not None and self.obj_ids is not None and self.place_ws_ids is not None
        ), "Behaviour.step: mockup behaviour expects reset() to be called first"

        agn_str = " or ".join(uri.n3(namespace_manager=self._ns_manager) for uri in self.agn_ids)
        obj_str = " or ".join(uri.n3(namespace_manager=self._ns_manager) for uri in self.obj_ids)
        place_ws_str = " or ".join(
            uri.n3(namespace_manager=self._ns_manager) for uri in self.place_ws_ids
        )
        print(f"'{agn_str}' picks '{obj_str}'")
        sleep(0.05)
        print(f"'{agn_str}' places '{obj_str}' at '{place_ws_str}'")
        sleep(0.05)
        self.counter -= 1


def behaviour_mockup(context: Context, **kwargs: Any):
    params = load_str_params(param_names=[PARAM_AGN, PARAM_OBJ, PARAM_WS], **kwargs)

    behaviour_model = getattr(context, "behaviour_model", None)

    if behaviour_model is None:
        exec_model = getattr(context, "execution_model", None)
        assert isinstance(
            exec_model, ExecutionModel
        ), f"no valid 'execution_model' added to the context: {exec_model}"

        model_graph = getattr(context, "model_graph", None)
        assert isinstance(
            model_graph, Graph
        ), f"no 'model_graph' of type rdflib.Graph in context: {model_graph}"

        behaviour_model = exec_model.load_behaviour_impl(
            context=context,
            ns_manager=model_graph.namespace_manager,
        )
        context.behaviour_model = behaviour_model

    bhv = behaviour_model.behaviour
    assert bhv is not None, f"behaviour not processed for {behaviour_model.id}"
    bhv.reset(
        context=context,
        agn_id_str=params[PARAM_AGN],
        obj_id_str=params[PARAM_OBJ],
        ws_id_str=params[PARAM_WS],
    )
    while not bhv.is_finished(context=context):
        bhv.step(context=context)
