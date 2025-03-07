# SPDX-License-Identifier:  GPL-3.0-or-later
from jinja2 import Environment, FileSystemLoader, Template
from typing import List
from bdd_dsl.models.queries import (
    Q_PREDICATE,
    Q_BDD_PRED_LOCATED_AT,
    Q_BDD_PRED_IS_NEAR,
    Q_BDD_PRED_IS_HELD,
    Q_HAS_EVENT,
)
from bdd_dsl.models.frames import (
    FR_TYPE,
    FR_NAME,
    FR_OBJECTS,
    FR_AGENTS,
    FR_WS,
    FR_CRITERIA,
    FR_SCENARIO,
    FR_GIVEN,
    FR_WHEN,
    FR_THEN,
    FR_CLAUSES,
    FR_FLUENT_DATA,
)
from bdd_dsl.utils.common import get_valid_var_name
from bdd_dsl.exception import BDDConstraintViolation


def _load_template(template_name: str, env: Environment) -> Template:
    return env.get_template(template_name)


def load_template(template_name: str, dir_name: str) -> Template:
    env = Environment(loader=FileSystemLoader(dir_name), autoescape=True)
    return _load_template(template_name, env)


def load_templates(template_names: List[str], dir_name: str) -> List[Template]:
    env = Environment(loader=FileSystemLoader(dir_name), autoescape=True)
    return [_load_template(name, env) for name in template_names]


def extract_valid_ref_names(fluent_data: dict, ref_type: str) -> list:
    if ref_type not in fluent_data:
        return []

    names = []
    if isinstance(fluent_data[ref_type], dict):
        names.append(get_valid_var_name(fluent_data[ref_type][FR_NAME]))
    elif isinstance(fluent_data[ref_type], list):
        for agent_data in fluent_data[ref_type]:
            names.append(get_valid_var_name(agent_data[FR_NAME]))
    return names


def clause_string_from_fluent_data(fluent_data: dict, feature_clauses) -> str:
    fluent_name = fluent_data[FR_NAME]
    fluent_data = feature_clauses[fluent_name]
    clause_type = fluent_data[Q_PREDICATE][FR_TYPE]

    object_names = extract_valid_ref_names(fluent_data, FR_OBJECTS)
    num_obj_refs = len(object_names)

    ws_names = extract_valid_ref_names(fluent_data, FR_WS)
    num_ws_refs = len(ws_names)

    agent_names = extract_valid_ref_names(fluent_data, FR_AGENTS)
    num_agent_refs = len(agent_names)

    unexpected_ref_cnt_msg = (
        f"fluent '{fluent_name}' (predicate type '{clause_type}') has unexpected reference counts:"
        f" '{num_obj_refs}' to objects, '{num_ws_refs}' to workspaces, '{num_agent_refs}' to agents"
    )

    if clause_type == Q_BDD_PRED_LOCATED_AT:
        if num_obj_refs != 1 or num_ws_refs != 1 or num_agent_refs != 0:
            raise BDDConstraintViolation(unexpected_ref_cnt_msg)
        return f'"<{object_names[0]}>" is located at "<{ws_names[0]}>"'

    if clause_type == Q_BDD_PRED_IS_NEAR:
        if num_obj_refs != 1 or num_agent_refs != 1 or num_ws_refs != 0:
            raise BDDConstraintViolation(unexpected_ref_cnt_msg)
        return f'"<{agent_names[0]}>" is near "<{object_names[0]}>"'

    if clause_type == Q_BDD_PRED_IS_HELD:
        if num_obj_refs != 1 or num_agent_refs != 1 or num_ws_refs != 0:
            raise BDDConstraintViolation(unexpected_ref_cnt_msg)
        return f'"<{object_names[0]}>" is held by "<{agent_names[0]}>"'

    raise ValueError(f"unexpected predicate type '{clause_type}'")


def create_clauses_strings(
    scenario_clauses: List[dict], feature_clauses: dict, first_clause_prefix: str
) -> List[str]:
    clause_strings = []
    for idx, clause_data in enumerate(scenario_clauses):
        prefix = first_clause_prefix if idx == 0 else "And"
        clause_strings.append(
            f"{prefix} {clause_string_from_fluent_data(clause_data, feature_clauses)}"
        )
    return clause_strings


def create_given_clauses_strings(scenario_clauses: List[dict], feature_clauses: dict) -> List[str]:
    return create_clauses_strings(scenario_clauses, feature_clauses, "Given")


def create_then_clauses_strings(scenario_clauses: List[dict], feature_clauses: dict) -> List[str]:
    return create_clauses_strings(scenario_clauses, feature_clauses, "Then")


def prepare_gherkin_feature_data(us_data: dict):
    for scenario_data in us_data[FR_CRITERIA]:
        scenario_data["given_clauses"] = create_given_clauses_strings(
            scenario_data[FR_SCENARIO][FR_GIVEN][FR_CLAUSES], us_data[FR_FLUENT_DATA]
        )
        scenario_data["then_clauses"] = create_then_clauses_strings(
            scenario_data[FR_SCENARIO][FR_THEN][FR_CLAUSES], us_data[FR_FLUENT_DATA]
        )
        if Q_HAS_EVENT in scenario_data[FR_SCENARIO][FR_WHEN]:
            scenario_data["when_event"] = scenario_data[FR_SCENARIO][FR_WHEN][Q_HAS_EVENT][FR_NAME]
