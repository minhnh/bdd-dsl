# SPDX-License-Identifier:  GPL-3.0-or-later
from itertools import product
from jinja2 import Environment, FileSystemLoader, Template
from typing import Iterable, Optional
from rdflib import Graph, URIRef
from rdflib.namespace import NamespaceManager
from rdf_utils.caching import read_file_and_cache, read_url_and_cache
from rdf_utils.naming import get_valid_var_name
from bdd_dsl.models.frames import (
    FR_AGENTS,
    FR_OBJECTS,
    FR_SCENE,
    FR_NAME,
    FR_CRITERIA,
    FR_VARIABLES,
    FR_VARIATIONS,
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


def get_task_variation_table(
    task_var: TaskVariationModel, ns_manager: NamespaceManager
) -> tuple[list[str], list[Iterable[str]]]:
    if URI_BDD_TYPE_CART_PRODUCT in task_var.types:
        var_names = []
        var_val_str_sets = []

        var_uri_list = task_var.get_attr(key=URI_BDD_PRED_VAR_LIST)
        var_value_sets = task_var.get_attr(key=URI_BDD_PRED_OF_SETS)
        assert var_uri_list is not None and var_value_sets is not None
        assert len(var_uri_list) == len(var_value_sets)

        for i in range(len(var_uri_list)):
            var_names.append(get_valid_var_name(var_uri_list[i].n3(namespace_manager=ns_manager)))

            var_val_strings = []
            set_data = var_value_sets[i]
            uri_iterable = None
            if isinstance(set_data, URIRef) and set_data in task_var.set_enums:
                # set enumeration
                uri_iterable = task_var.set_enums[set_data].enumerate()
            elif isinstance(set_data, list):
                # list
                uri_iterable = set_data
            else:
                raise RuntimeError(
                    f"get_task_variation_table: {task_var.id}: sets for cartesian product"
                    f" not list or URIRef: {var_value_sets[i]}"
                )

            for val_data in uri_iterable:
                if isinstance(val_data, URIRef):
                    var_val_strings.append(val_data.n3(namespace_manager=ns_manager))
                    continue

                val_data_strings = []
                assert isinstance(
                    val_data, Iterable
                ), f"variable value for '{task_var.id}' is not URIRef or Iterable: {val_data}"
                for uri in val_data:
                    assert isinstance(
                        uri, URIRef
                    ), f"get_task_variation_table: {task_var.id}: not a URIRef {uri}"
                    val_data_strings.append(uri.n3(namespace_manager=ns_manager))

                assert (
                    len(val_data_strings) > 0
                ), f"get_task_variation_table: {task_var.id}: empty iterable: {val_data}"
                if len(val_data_strings) == 1:
                    var_val_strings.append(val_data_strings[0])
                else:
                    var_val_strings.append(str(val_data_strings))

            var_val_str_sets.append(var_val_strings)

        return var_names, list(product(*var_val_str_sets))

    if URI_BDD_TYPE_TABLE_VAR in task_var.types:
        var_names = []
        var_val_str_rows = []
        var_uri_list = task_var.get_attr(key=URI_BDD_PRED_VAR_LIST)
        assert var_uri_list is not None
        for var_uri in var_uri_list:
            assert isinstance(var_uri, URIRef)
            var_names.append(get_valid_var_name(var_uri.n3(namespace_manager=ns_manager)))

        uri_rows = task_var.get_attr(key=URI_BDD_PRED_ROWS)
        assert uri_rows is not None
        for var_val_uri_row in uri_rows:
            var_val_strings = []
            for val_uri in var_val_uri_row:
                assert isinstance(val_uri, URIRef)
                var_val_strings.append(val_uri.n3(namespace_manager=ns_manager))
            var_val_str_rows.append(var_val_strings)

        return var_names, var_val_str_rows

    raise RuntimeError(f"TaskVariation '{task_var.id}' has unhandled types: {task_var.types}")


def prepare_scenario_variant_data(
    scr_var_model: ScenarioVariantModel,
    ns_manager: NamespaceManager,
) -> dict:
    scr_var_data = {}

    scr_var_data[FR_NAME] = scr_var_model.id.n3(namespace_manager=ns_manager)
    scr_var_data["behaviour"] = scr_var_model.scenario.bhv_id.n3(namespace_manager=ns_manager)

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
