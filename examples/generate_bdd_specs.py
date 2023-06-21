from os.path import join, dirname
from bdd_dsl.utils.json import load_metamodels, process_bdd_us_from_graph
from bdd_dsl.utils.jinja import (
    load_template,
    create_given_clauses_strings,
    create_then_clauses_strings,
)
from bdd_dsl.models.queries import Q_HAS_EVENT
from bdd_dsl.models.frames import (
    FR_NAME,
    FR_CRITERIA,
    FR_SCENARIO,
    FR_GIVEN,
    FR_WHEN,
    FR_THEN,
    FR_CLAUSES,
    FR_FLUENT_DATA,
)
from bdd_dsl.utils.common import get_valid_filename


PKG_ROOT = join(dirname(__file__), "..")
MODELS_PATH = join(PKG_ROOT, "models")
JINJA_TMPL_DIR = join(MODELS_PATH, "jinja")
JINJA_FEATURE_TMPL = "feature.jinja"
GENERATED_DIR = join(PKG_ROOT, "examples", "generated")


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


def main():
    g = load_metamodels()
    g.parse(join(MODELS_PATH, "acceptance-criteria", "bdd-templates-pick.json"), format="json-ld")
    g.parse(join(MODELS_PATH, "acceptance-criteria", "bdd-pick.json"), format="json-ld")
    g.parse(join(MODELS_PATH, "coordination", "pickup-events.json"), format="json-ld")
    g.parse(join(MODELS_PATH, "brsu-robots.json"), format="json-ld")
    g.parse(join(MODELS_PATH, "brsu-env.json"), format="json-ld")

    processed_bdd_data = process_bdd_us_from_graph(g)
    feature_template = load_template(JINJA_FEATURE_TMPL, JINJA_TMPL_DIR)
    for us_data in processed_bdd_data:
        us_name = us_data[FR_NAME]
        prepare_gherkin_feature_data(us_data)
        feature_content = feature_template.render(data=us_data)
        feature_filename = f"{get_valid_filename(us_name)}.feature"
        filepath = join(GENERATED_DIR, feature_filename)
        with open(filepath, mode="w", encoding="utf-8") as of:
            of.write(feature_content)
            print(f"... wrote {filepath}")


if __name__ == "__main__":
    main()
