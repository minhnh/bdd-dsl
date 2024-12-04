# SPDX-License-Identifier:  GPL-3.0-or-later
from typing import Any, Iterable, Optional, Protocol
from itertools import product
from jinja2 import Environment, FileSystemLoader, Template
from rdf_utils.models.common import ModelBase
from rdflib import Graph, URIRef
from rdflib.namespace import NamespaceManager
from rdf_utils.caching import read_file_and_cache, read_url_and_cache
from bdd_dsl.models.clauses import (
    FluentClauseModel,
    TimeConstraintModel,
    WhenBehaviourModel,
)
from bdd_dsl.models.frames import (
    FR_AGENTS,
    FR_OBJECTS,
    FR_SCENE,
    FR_NAME,
    FR_CRITERIA,
    FR_VARIATIONS,
    FR_WS,
)
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_OF_SETS,
    URI_BDD_PRED_ROWS,
    URI_BDD_PRED_VAR_LIST,
    URI_BDD_TYPE_CART_PRODUCT,
    URI_BDD_TYPE_TABLE_VAR,
    URI_BDD_PRED_REF_AGN,
    URI_BDD_PRED_REF_OBJ,
    URI_BDD_PRED_REF_WS,
    URI_BDD_TYPE_IS_HELD,
    URI_BDD_TYPE_LOCATED_AT,
    URI_BHV_PRED_PICK_WS,
    URI_BHV_PRED_PLACE_WS,
    URI_BHV_PRED_TARGET_AGN,
    URI_BHV_PRED_TARGET_OBJ,
    URI_BHV_TYPE_PICKPLACE,
    URI_TIME_PRED_REF_EVT,
    URI_TIME_TYPE_AFTER_EVT,
    URI_TIME_TYPE_BEFORE_EVT,
)
from bdd_dsl.models.user_story import (
    ForAllModel,
    IHasClause,
    ScenarioVariantModel,
    TaskVariationModel,
    ThereExistsModel,
    UserStoryLoader,
)


def load_template_from_file(file_path: str) -> Template:
    """Create template instance from text content of a file.

    Not using Jinja's environment loading mechanism may break more advanced features like
    template inheritance and filters.
    """
    return Template(read_file_and_cache(file_path), autoescape=True)


def load_template_from_url(url: str) -> Template:
    """Create template instance by downloading a remote template URL.

    Not using Jinja's environment loading mechanism may break more advanced features like
    template inheritance and filters.
    """
    return Template(read_url_and_cache(url), autoescape=True)


def load_template(template_name: str, dir_name: str) -> Template:
    env = Environment(loader=FileSystemLoader(dir_name), autoescape=True)
    return env.get_template(template_name)


def get_task_variations(task_var: TaskVariationModel) -> tuple[list[URIRef], list[Iterable[Any]]]:
    var_uri_list = task_var.get_attr(key=URI_BDD_PRED_VAR_LIST)
    assert isinstance(
        var_uri_list, list
    ), f"TaskVariation '{task_var.id}' does not have a list of variables as attr"

    if URI_BDD_TYPE_CART_PRODUCT in task_var.types:
        var_value_sets = task_var.get_attr(key=URI_BDD_PRED_OF_SETS)
        assert isinstance(
            var_value_sets, list
        ), f"TaskVariation '{task_var.id}' does not have a list of variable values as attr"
        assert len(var_uri_list) == len(
            var_value_sets
        ), f"TaskVariation '{task_var.id}': number of varibles doesn't match set of values"

        uri_iterables = []
        for set_data in var_value_sets:
            if isinstance(set_data, URIRef) and set_data in task_var.set_enums:
                # set enumeration
                uri_iterables.append(task_var.set_enums[set_data].enumerate())
            elif isinstance(set_data, list):
                # list
                uri_iterables.append(set_data)
            else:
                raise RuntimeError(
                    f"TaskVariation {task_var.id}: sets for cartesian product not list or URIRef: {set_data}"
                )

        return var_uri_list, list(product(*uri_iterables))

    if URI_BDD_TYPE_TABLE_VAR in task_var.types:
        uri_rows = task_var.get_attr(key=URI_BDD_PRED_ROWS)
        assert isinstance(
            uri_rows, list
        ), f"TaskVariation {task_var.id}: table rows are not a list: {uri_rows}"
        return var_uri_list, uri_rows

    raise RuntimeError(f"TaskVariation '{task_var.id}' has unhandled types: {task_var.types}")


class TimeConstraintToStringProtocol(Protocol):
    """Protocol for functions that transform fluent clauses to time constraint strings."""

    def __call__(self, tc: TimeConstraintModel, ns_manager: NamespaceManager) -> str: ...


def get_tc_str_before_event(tc: TimeConstraintModel, ns_manager: NamespaceManager) -> str:
    evt_uri = tc.get_attr(key=URI_TIME_PRED_REF_EVT)
    assert isinstance(
        evt_uri, URIRef
    ), f"TimeConstraint '{tc.id}' of types '{tc.types}' doesn't ref an event's URI: {evt_uri}"
    evt_uri_str = evt_uri.n3(ns_manager)
    return f'before event "{evt_uri_str}"'


def get_tc_str_after_event(tc: TimeConstraintModel, ns_manager: NamespaceManager) -> str:
    evt_uri = tc.get_attr(key=URI_TIME_PRED_REF_EVT)
    assert isinstance(
        evt_uri, URIRef
    ), f"TimeConstraint '{tc.id}' of types '{tc.types}' doesn't ref an event's URI: {evt_uri}"
    evt_uri_str = evt_uri.n3(ns_manager)
    return f'after event "{evt_uri_str}"'


DEFAULT_TIME_CSTR_STR_GENS = {
    URI_TIME_TYPE_BEFORE_EVT: get_tc_str_before_event,
    URI_TIME_TYPE_AFTER_EVT: get_tc_str_after_event,
}


class FluentClauseToStringProtocol(Protocol):
    """Protocol for functions that transform fluent clauses to Gherkin strings."""

    def __call__(
        self, clause: FluentClauseModel, var_values: dict[URIRef, Any], ns_manager: NamespaceManager
    ) -> str: ...


def _var_val_to_str(var_val, ns_manager: NamespaceManager) -> str:
    if isinstance(var_val, str):
        return var_val

    if isinstance(var_val, URIRef):
        return var_val.n3(namespace_manager=ns_manager)

    if isinstance(var_val, Iterable):
        uri_str_list = []
        for uri in var_val:
            assert isinstance(uri, URIRef), f"not an Iterable of URIRef: {var_val}"
            uri_str_list.append(uri.n3(namespace_manager=ns_manager))

        return str(uri_str_list)

    raise RuntimeError(f"_var_val_to_str: unhandled types: {var_val}")


def get_fc_str_located_at(
    clause: FluentClauseModel, var_values: dict[URIRef, Any], ns_manager: NamespaceManager
) -> str:
    assert (
        URI_BDD_PRED_REF_OBJ in clause.variable_by_role
    ), f"LocatedAt fluent '{clause.id}' does not have 'ref-obj' property"
    obj_id = clause.variable_by_role[URI_BDD_PRED_REF_OBJ][0]
    assert isinstance(
        obj_id, URIRef
    ), f"LocatedAt fluent '{clause.id}' does not have URI 'ref-obj' property"
    assert (
        obj_id in var_values
    ), f"LocatedAt fluent '{clause.id}': no value for obj '{obj_id}', available vars: {list(var_values.keys())}"
    obj_value_str = _var_val_to_str(var_val=var_values[obj_id], ns_manager=ns_manager)

    assert (
        URI_BDD_PRED_REF_WS in clause.variable_by_role
    ), f"LocatedAt fluent '{clause.id}' does not have 'ref-ws' property"
    ws_id = clause.variable_by_role[URI_BDD_PRED_REF_WS][0]
    assert isinstance(
        ws_id, URIRef
    ), f"LocatedAt fluent '{clause.id}' does not have URI 'ref-ws' property"
    assert (
        ws_id in var_values
    ), f"LocatedAt fluent '{clause.id}': no value for ws '{ws_id}', available vars: {list(var_values.keys())}"
    ws_value_str = _var_val_to_str(var_val=var_values[ws_id], ns_manager=ns_manager)

    return f'"{obj_value_str}" is located at "{ws_value_str}"'


def get_fc_str_is_held(
    clause: FluentClauseModel, var_values: dict[URIRef, Any], ns_manager: NamespaceManager
) -> str:
    assert (
        URI_BDD_PRED_REF_OBJ in clause.variable_by_role
    ), f"IsHeldBy fluent '{clause.id}' does not have 'ref-obj' property"
    obj_id = clause.variable_by_role[URI_BDD_PRED_REF_OBJ][0]
    assert isinstance(
        obj_id, URIRef
    ), f"IsHeldBy fluent '{clause.id}' does not have URI 'ref-obj' property"
    assert (
        obj_id in var_values
    ), f"IsHeldBy fluent '{clause.id}': no value for obj '{obj_id}', available vars: {list(var_values.keys())}"
    obj_value_str = _var_val_to_str(var_val=var_values[obj_id], ns_manager=ns_manager)

    assert (
        URI_BDD_PRED_REF_AGN in clause.variable_by_role
    ), f"IsHeldBy fluent '{clause.id}' does not have 'ref-agn' property"
    agn_id = clause.variable_by_role[URI_BDD_PRED_REF_AGN][0]
    assert isinstance(
        agn_id, URIRef
    ), f"IsHeldBy fluent '{clause.id}' does not have URI 'ref-agn' property"
    assert (
        agn_id in var_values
    ), f"IsHeldBy fluent '{clause.id}': no value for agn '{agn_id}', available vars: {list(var_values.keys())}"
    agn_value_str = _var_val_to_str(var_val=var_values[agn_id], ns_manager=ns_manager)

    return f'"{obj_value_str}" is held by "{agn_value_str}"'


DEFAULT_FLUENT_CLAUSE_STR_GENS = {
    URI_BDD_TYPE_LOCATED_AT: get_fc_str_located_at,
    URI_BDD_TYPE_IS_HELD: get_fc_str_is_held,
}


class WhenBhvToStringProtocol(Protocol):
    """Protocol for functions that transform WhenBehaviour clauses to Gherkin strings."""

    def __call__(
        self,
        when_bhv: WhenBehaviourModel,
        var_values: dict[URIRef, Any],
        ns_manager: NamespaceManager,
    ) -> str: ...


def _get_attr_var_val_str(
    model: ModelBase, key: URIRef, var_values: dict[URIRef, Any], ns_manager: NamespaceManager
) -> str:
    attr_id = model.get_attr(key=key)
    assert isinstance(
        attr_id, URIRef
    ), f"'{model.id}' doesn't have a URI for property '{key}': {attr_id}"
    assert (
        attr_id in var_values
    ), f"'{model.id}': no value for '{attr_id}', available vars: {list(var_values.keys())}"
    attr_val = var_values[attr_id]
    return _var_val_to_str(var_val=attr_val, ns_manager=ns_manager)


def get_bhv_str_pickplace(
    when_bhv: WhenBehaviourModel, var_values: dict[URIRef, Any], ns_manager: NamespaceManager
) -> str:
    obj_val_str = _get_attr_var_val_str(
        model=when_bhv, key=URI_BHV_PRED_TARGET_OBJ, var_values=var_values, ns_manager=ns_manager
    )

    agn_val_str = _get_attr_var_val_str(
        model=when_bhv, key=URI_BHV_PRED_TARGET_AGN, var_values=var_values, ns_manager=ns_manager
    )

    pick_ws_val_str = _get_attr_var_val_str(
        model=when_bhv, key=URI_BHV_PRED_PICK_WS, var_values=var_values, ns_manager=ns_manager
    )

    place_ws_val_str = _get_attr_var_val_str(
        model=when_bhv, key=URI_BHV_PRED_PLACE_WS, var_values=var_values, ns_manager=ns_manager
    )

    return f'"{agn_val_str}" picks "{obj_val_str}" from "{pick_ws_val_str}" and places it at "{place_ws_val_str}"'


DEFAULT_WHEN_BHV_STR_GENS = {
    URI_BHV_TYPE_PICKPLACE: get_bhv_str_pickplace,
}


class GherkinClauseStrGen(object):
    _tc_transformers: dict[URIRef, TimeConstraintToStringProtocol]
    _fc_transformers: dict[URIRef, FluentClauseToStringProtocol]
    _wb_transformers: dict[URIRef, WhenBhvToStringProtocol]

    def __init__(
        self,
        tc_transformers: dict[URIRef, TimeConstraintToStringProtocol],
        fc_transformers: dict[URIRef, FluentClauseToStringProtocol],
        wb_transformers: dict[URIRef, WhenBhvToStringProtocol],
    ) -> None:
        self._tc_transformers = tc_transformers
        self._fc_transformers = fc_transformers
        self._wb_transformers = wb_transformers

    def get_fluent_clause_str(
        self, clause: FluentClauseModel, var_values: dict[URIRef, Any], ns_manager: NamespaceManager
    ) -> str:
        for fluent_type in self._fc_transformers:
            if fluent_type not in clause.fluent.types:
                continue

            for tc_type in self._tc_transformers:
                if tc_type not in clause.time_constraint.types:
                    continue

                clause_str = self._fc_transformers[fluent_type](
                    clause=clause, var_values=var_values, ns_manager=ns_manager
                )
                tc_str = self._tc_transformers[tc_type](
                    tc=clause.time_constraint, ns_manager=ns_manager
                )
                return f"{clause_str} {tc_str}"

        raise RuntimeError(
            f"get_fluent_clause_str: clause '{clause.id}' has unhandled fluent types: {clause.fluent.types}"
        )

    def get_bhv_str(
        self,
        when_bhv: WhenBehaviourModel,
        var_values: dict[URIRef, Any],
        ns_manager: NamespaceManager,
    ) -> str:
        for bhv_type in self._wb_transformers:
            if bhv_type not in when_bhv.behaviour.types:
                continue

            return self._wb_transformers[bhv_type](
                when_bhv=when_bhv, var_values=var_values, ns_manager=ns_manager
            )

        raise RuntimeError(
            f"get_bhv_str: WhenBehaviour '{when_bhv.id}' has unhandled behaviour types: {when_bhv.behaviour.types}"
        )


def get_gherkin_clauses_re(
    has_clause_model: IHasClause,
    clause_str_gen: GherkinClauseStrGen,
    ns_manager: NamespaceManager,
    var_values: dict[URIRef, Any],
    clause_list: list[str],
) -> None:
    # prepare values for quantified var in ThereExists clauses
    for exists_id in has_clause_model.exists_clauses:
        exists_model = has_clause_model.clauses[exists_id]
        assert isinstance(
            exists_model, ThereExistsModel
        ), f"'{exists_id}' is not a ThereExistsModel"
        if isinstance(exists_model.in_set, list):
            exists_set = exists_model.in_set
        elif isinstance(exists_model.in_set, URIRef):
            assert (
                exists_model.in_set in var_values
            ), f"ThereExists '{exists_model.id}': no value set for URI 'in-set', available vars: {list(var_values.keys())}"
            exists_set = var_values[exists_model.in_set]
            assert isinstance(
                exists_set, Iterable
            ), f"ThereExists '{exists_model.id}': value 'in-set' not an Iterable: {exists_set}"
        else:
            raise RuntimeError(
                f"ThereExists '{exists_model.id}': unhandled type for 'in-set': {exists_model.in_set}"
            )
        exists_str_set = []
        for elem_id in exists_set:
            assert isinstance(
                elem_id, URIRef
            ), f"ThereExists '{exists_model.id}': not a URI: {elem_id}"
            exists_str_set.append(elem_id.n3(namespace_manager=ns_manager))
        var_values[exists_model.quantified_var] = f"any of {exists_str_set}"

    for g_clause_id in has_clause_model.clauses_by_role[has_clause_model.scenario.given]:
        g_clause = has_clause_model.clauses[g_clause_id]
        if isinstance(g_clause, FluentClauseModel):
            clause_str = clause_str_gen.get_fluent_clause_str(
                clause=g_clause, var_values=var_values, ns_manager=ns_manager
            )
            clause_list.append(f"Given {clause_str}")
            continue

        if isinstance(g_clause, ThereExistsModel):
            get_gherkin_clauses_re(
                has_clause_model=g_clause,
                clause_str_gen=clause_str_gen,
                ns_manager=ns_manager,
                var_values=var_values,
                clause_list=clause_list,
            )
            continue

        raise RuntimeError(f"clause '{g_clause_id}' not a fluent clause model: {type(g_clause)}")

    for w_clause_id in has_clause_model.clauses_by_role[has_clause_model.scenario.when]:
        w_clause = has_clause_model.clauses[w_clause_id]
        if isinstance(w_clause, WhenBehaviourModel):
            bhv_str = clause_str_gen.get_bhv_str(
                when_bhv=w_clause, var_values=var_values, ns_manager=ns_manager
            )
            clause_list.append(f"When {bhv_str}")
            continue

        if isinstance(w_clause, ForAllModel):
            if isinstance(w_clause.in_set, list):
                forall_set = w_clause.in_set
            elif isinstance(w_clause.in_set, URIRef):
                assert (
                    w_clause.in_set in var_values
                ), f"ForAll '{w_clause.id}': no value set for URI 'in-set', available vars: {list(var_values.keys())}"
                forall_set = var_values[w_clause.in_set]
                assert isinstance(
                    forall_set, Iterable
                ), f"ForAll '{w_clause.id}': value 'in-set' not an Iterable: {forall_set}"
            else:
                raise RuntimeError(
                    f"ForAll '{w_clause.id}': unhandled type for 'in-set': {w_clause.in_set}"
                )

            for quant_val in forall_set:
                var_values[w_clause.quantified_var] = quant_val
                get_gherkin_clauses_re(
                    has_clause_model=w_clause,
                    clause_str_gen=clause_str_gen,
                    ns_manager=ns_manager,
                    var_values=var_values,
                    clause_list=clause_list,
                )
            continue

    for t_clause_id in has_clause_model.clauses_by_role[has_clause_model.scenario.then]:
        t_clause = has_clause_model.clauses[t_clause_id]
        if isinstance(t_clause, FluentClauseModel):
            clause_str = clause_str_gen.get_fluent_clause_str(
                clause=t_clause, var_values=var_values, ns_manager=ns_manager
            )
            clause_list.append(f"Then {clause_str}")
            continue

        if isinstance(t_clause, ThereExistsModel):
            get_gherkin_clauses_re(
                has_clause_model=t_clause,
                clause_str_gen=clause_str_gen,
                ns_manager=ns_manager,
                var_values=var_values,
                clause_list=clause_list,
            )
            continue

        raise RuntimeError(f"clause '{t_clause_id}' not a fluent clause model: {type(t_clause)}")


def prepare_scenario_variant_data(
    scr_var_model: ScenarioVariantModel,
    ns_manager: NamespaceManager,
    tc_transformers: dict[URIRef, TimeConstraintToStringProtocol] = DEFAULT_TIME_CSTR_STR_GENS,
    fc_transformers: dict[URIRef, FluentClauseToStringProtocol] = DEFAULT_FLUENT_CLAUSE_STR_GENS,
    wb_transformers: dict[URIRef, WhenBhvToStringProtocol] = DEFAULT_WHEN_BHV_STR_GENS,
) -> dict:
    scr_var_name = scr_var_model.id.n3(namespace_manager=ns_manager)
    scr_var_data = {FR_NAME: scr_var_name, FR_VARIATIONS: []}

    var_uri_list, var_vals_list = get_task_variations(scr_var_model.task_variation)
    var_count = 1
    string_gen = GherkinClauseStrGen(
        tc_transformers=tc_transformers,
        fc_transformers=fc_transformers,
        wb_transformers=wb_transformers,
    )
    for var_value_set in var_vals_list:
        var_values = dict(zip(var_uri_list, var_value_set))

        clauses = []
        get_gherkin_clauses_re(
            has_clause_model=scr_var_model,
            clause_str_gen=string_gen,
            ns_manager=ns_manager,
            var_values=var_values,
            clause_list=clauses,
        )
        scr_var_data[FR_VARIATIONS].append(
            {FR_NAME: f"{scr_var_name} -- {var_count}", "clauses": clauses}
        )
        var_count += 1

    return scr_var_data


def prepare_jinja2_template_data(
    us_loader: UserStoryLoader, full_graph: Graph, ns_manager: Optional[NamespaceManager] = None
) -> list[dict]:
    """TODO(minhnh): specify which template"""
    if ns_manager is None:
        ns_manager = full_graph.namespace_manager

    us_var_dict = us_loader.get_us_scenario_variants()
    jinja_data = []
    for us_id, scr_var_set in us_var_dict.items():
        us_id_str = us_id.n3(namespace_manager=ns_manager)
        us_data = {FR_NAME: us_id_str, FR_CRITERIA: []}

        # TODO(minhnh): handles a UserStory having multiple scenes, since scenes are linked to
        # a ScenarioTemplate, multiple of which can appear in a UserStory. This can perhaps be
        # a constraint on USs, but for now just raise an error
        scene_data = {}

        for scr_var_id in scr_var_set:
            scr_var = us_loader.load_scenario_variant(full_graph=full_graph, variant_id=scr_var_id)

            # Scene data
            scene_id_str = scr_var.scene.id.n3(namespace_manager=ns_manager)
            if FR_NAME not in scene_data:
                scene_data[FR_NAME] = scene_id_str

                obj_list = []
                for obj_id in scr_var.scene.objects:
                    obj_list.append(obj_id.n3(namespace_manager=ns_manager))
                if len(obj_list) > 0:
                    scene_data[FR_OBJECTS] = obj_list

                ws_list = []
                for ws_id in scr_var.scene.workspaces.keys():
                    ws_list.append(ws_id.n3(namespace_manager=ns_manager))
                if len(ws_list) > 0:
                    scene_data[FR_WS] = ws_list

                agn_list = []
                for agn_id in scr_var.scene.agents:
                    agn_list.append(agn_id.n3(namespace_manager=ns_manager))
                if len(agn_list) > 0:
                    scene_data[FR_AGENTS] = agn_list
            else:
                if scene_id_str != scene_data[FR_NAME]:
                    raise ValueError(
                        f"can't handle multiple scenes for US '{us_id_str}': {scene_data[FR_NAME]}, {scene_id_str}"
                    )

            # ScenarioVariant data
            scr_var_data = prepare_scenario_variant_data(
                scr_var_model=scr_var, ns_manager=ns_manager
            )

            us_data[FR_CRITERIA].append(scr_var_data)

        us_data[FR_SCENE] = scene_data

        jinja_data.append(us_data)

    return jinja_data
