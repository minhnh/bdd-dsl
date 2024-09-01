# SPDX-License-Identifier:  GPL-3.0-or-later
from itertools import product
from jinja2 import Environment, FileSystemLoader, Template
from typing import Iterable, List, Optional
from rdflib import Graph, URIRef
from rdflib.namespace import NamespaceManager
from rdf_utils.caching import read_file_and_cache, read_url_and_cache
from rdf_utils.naming import get_valid_var_name
from bdd_dsl.exception import BDDConstraintViolation
from bdd_dsl.models.queries import (
    Q_BDD_PRED_LOCATED_AT,
    Q_BDD_PRED_IS_NEAR,
    Q_BDD_PRED_IS_HELD,
    Q_HAS_EVENT,
)
from bdd_dsl.models.frames import (
    FR_AGENTS,
    FR_OBJECTS,
    FR_SCENE,
    FR_TYPE,
    FR_FLUENTS,
    FR_NAME,
    FR_VAR_OBJ,
    FR_VAR_WS,
    FR_VAR_AGN,
    FR_CRITERIA,
    FR_SCENARIO,
    FR_GIVEN,
    FR_VARIABLES,
    FR_VARIATIONS,
    FR_WHEN,
    FR_THEN,
    FR_HOLDS,
    FR_CLAUSES_DATA,
    FR_WS,
)
from bdd_dsl.models.urirefs import (
    URI_BDD_PRED_OF_SETS,
    URI_BDD_PRED_ROWS,
    URI_BDD_PRED_VAR_LIST,
    URI_BDD_TYPE_CART_PRODUCT,
    URI_BDD_TYPE_TABLE_VAR,
)
from bdd_dsl.models.user_story import (
    ScenarioVariantModel,
    TaskVariationModel,
    UserStoryLoader,
    get_clause_str,
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


def extract_valid_ref_names(clause_data: dict, ref_type: str) -> list:
    if ref_type not in clause_data:
        return []

    names = []
    if isinstance(clause_data[ref_type], dict):
        names.append(get_valid_var_name(clause_data[ref_type][FR_NAME]))
    elif isinstance(clause_data[ref_type], list):
        for agent_data in clause_data[ref_type]:
            names.append(get_valid_var_name(agent_data[FR_NAME]))
    return names


def clause_string_from_clause_data(clause_data: dict, feature_clauses) -> str:
    clause_id = clause_data[FR_NAME]
    clause_data = feature_clauses[clause_id]
    fluent_id = clause_data[FR_HOLDS][FR_NAME]
    assert fluent_id in feature_clauses[FR_FLUENTS]
    fluent_type = feature_clauses[FR_FLUENTS][fluent_id][FR_TYPE]
    fluent_type_set = set()
    if isinstance(fluent_type, list):
        for t in fluent_type:
            fluent_type_set.add(t)
    else:
        fluent_type_set.add(fluent_type)

    object_names = extract_valid_ref_names(clause_data, FR_VAR_OBJ)
    num_obj_refs = len(object_names)

    ws_names = extract_valid_ref_names(clause_data, FR_VAR_WS)
    num_ws_refs = len(ws_names)

    agent_names = extract_valid_ref_names(clause_data, FR_VAR_AGN)
    num_agent_refs = len(agent_names)

    unexpected_ref_cnt_msg = (
        f"fluent '{clause_id}' (predicate type '{fluent_type}') has unexpected reference counts:"
        f" '{num_obj_refs}' to objects, '{num_ws_refs}' to workspaces, '{num_agent_refs}' to agents"
    )

    if Q_BDD_PRED_LOCATED_AT in fluent_type_set:
        if num_obj_refs != 1 or num_ws_refs != 1 or num_agent_refs != 0:
            raise BDDConstraintViolation(unexpected_ref_cnt_msg)
        return f'"<{object_names[0]}>" is located at "<{ws_names[0]}>"'

    if Q_BDD_PRED_IS_NEAR in fluent_type_set:
        if num_obj_refs != 1 or num_agent_refs != 1 or num_ws_refs != 0:
            raise BDDConstraintViolation(unexpected_ref_cnt_msg)
        return f'"<{agent_names[0]}>" is near "<{object_names[0]}>"'

    if Q_BDD_PRED_IS_HELD in fluent_type_set:
        if num_obj_refs != 1 or num_agent_refs != 1 or num_ws_refs != 0:
            raise BDDConstraintViolation(unexpected_ref_cnt_msg)
        return f'"<{object_names[0]}>" is held by "<{agent_names[0]}>"'

    raise ValueError(f"unexpected predicate type '{fluent_type}'")


def create_clauses_strings(
    scenario_clauses: List[dict], feature_clauses: dict, first_clause_prefix: str
) -> List[str]:
    clause_strings = []
    for idx, clause_data in enumerate(scenario_clauses):
        prefix = first_clause_prefix if idx == 0 else "And"
        clause_strings.append(
            f"{prefix} {clause_string_from_clause_data(clause_data, feature_clauses)}"
        )
    return clause_strings


def create_given_clauses_strings(scenario_clauses: List[dict], feature_clauses: dict) -> List[str]:
    return create_clauses_strings(scenario_clauses, feature_clauses, "Given")


def create_then_clauses_strings(scenario_clauses: List[dict], feature_clauses: dict) -> List[str]:
    return create_clauses_strings(scenario_clauses, feature_clauses, "Then")


def prepare_gherkin_feature_data(us_data: dict):
    for scenario_data in us_data[FR_CRITERIA]:
        scenario_data["given_clauses"] = create_given_clauses_strings(
            scenario_data[FR_SCENARIO][FR_GIVEN], us_data[FR_CLAUSES_DATA]
        )
        scenario_data["then_clauses"] = create_then_clauses_strings(
            scenario_data[FR_SCENARIO][FR_THEN], us_data[FR_CLAUSES_DATA]
        )
        if Q_HAS_EVENT in scenario_data[FR_SCENARIO][FR_WHEN]:
            scenario_data["when_event"] = scenario_data[FR_SCENARIO][FR_WHEN][Q_HAS_EVENT][FR_NAME]


def get_task_variation_table(
    task_var: TaskVariationModel, ns_manager: NamespaceManager
) -> tuple[list[str], list[Iterable[str]]]:
    if URI_BDD_TYPE_CART_PRODUCT in task_var.types:
        var_names = []
        var_val_str_sets = []

        var_uri_list = task_var.attributes[URI_BDD_PRED_VAR_LIST]
        var_values_uri_sets = task_var.attributes[URI_BDD_PRED_OF_SETS]
        assert len(var_uri_list) == len(var_values_uri_sets)

        for i in range(len(var_uri_list)):
            var_names.append(get_valid_var_name(var_uri_list[i].n3(namespace_manager=ns_manager)))

            var_val_strings = []
            for val_uri in var_values_uri_sets[i]:
                assert isinstance(val_uri, URIRef)
                var_val_strings.append(val_uri.n3(namespace_manager=ns_manager))
            var_val_str_sets.append(var_val_strings)

        return var_names, list(product(*var_val_str_sets))

    if URI_BDD_TYPE_TABLE_VAR in task_var.types:
        var_names = []
        var_val_str_rows = []
        for var_uri in task_var.attributes[URI_BDD_PRED_VAR_LIST]:
            assert isinstance(var_uri, URIRef)
            var_names.append(get_valid_var_name(var_uri.n3(namespace_manager=ns_manager)))

        for var_val_uri_row in task_var.attributes[URI_BDD_PRED_ROWS]:
            var_val_strings = []
            for val_uri in var_val_uri_row:
                assert isinstance(val_uri, URIRef)
                var_val_strings.append(val_uri.n3(namespace_manager=ns_manager))
            var_val_str_rows.append(var_val_strings)

        return var_names, var_val_str_rows

    raise RuntimeError(f"TaskVariation '{task_var.id}' has unhandled types: {task_var.types}")


def prepare_scenario_variant_date(
    scr_var_model: ScenarioVariantModel,
    ns_manager: NamespaceManager,
) -> dict:
    scr_var_data = {}

    scr_var_data[FR_NAME] = scr_var_model.id.n3(namespace_manager=ns_manager)
    scr_var_data["behaviour"] = scr_var_model.bhv_id.n3(namespace_manager=ns_manager)

    first_clause = True
    given_clause_strings = []
    for given_model in scr_var_model.get_given_clause_models():
        if first_clause:
            clause_str = "Given "
            first_clause = False
        else:
            clause_str = "And "
        clause_str += get_clause_str(clause=given_model, ns_manager=ns_manager)
        given_clause_strings.append(clause_str)

    first_clause = True
    then_clause_strings = []
    for then_model in scr_var_model.get_then_clause_models():
        if first_clause:
            first_clause = True
            clause_str = "Then "
        else:
            clause_str = "And "
        clause_str += get_clause_str(clause=then_model, ns_manager=ns_manager)
        then_clause_strings.append(clause_str)

    scr_var_data["given_clauses"] = given_clause_strings
    scr_var_data["then_clauses"] = then_clause_strings

    variable_list, variable_values = get_task_variation_table(
        scr_var_model.task_variation, ns_manager=ns_manager
    )
    scr_var_data[FR_VARIABLES] = variable_list
    scr_var_data[FR_VARIATIONS] = variable_values

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
                for obj_id in scr_var.scene.objects.keys():
                    obj_list.append(obj_id.n3(namespace_manager=ns_manager))
                if len(obj_list) > 0:
                    scene_data[FR_OBJECTS] = obj_list

                ws_list = []
                for ws_id in scr_var.scene.workspaces.keys():
                    ws_list.append(ws_id.n3(namespace_manager=ns_manager))
                if len(ws_list) > 0:
                    scene_data[FR_WS] = ws_list

                agn_list = []
                for agn_id in scr_var.scene.agents.keys():
                    agn_list.append(agn_id.n3(namespace_manager=ns_manager))
                if len(agn_list) > 0:
                    scene_data[FR_AGENTS] = agn_list
            else:
                if scene_id_str != scene_data[FR_NAME]:
                    raise ValueError(
                        f"can't handle multiple scenes for US '{us_id_str}': {scene_data[FR_NAME]}, {scene_id_str}"
                    )

            # ScenarioVariant data
            scr_var_data = prepare_scenario_variant_date(
                scr_var_model=scr_var, ns_manager=ns_manager
            )

            us_data[FR_CRITERIA].append(scr_var_data)

        us_data[FR_SCENE] = scene_data

        jinja_data.append(us_data)

    return jinja_data
