# SPDX-License-Identifier:  GPL-3.0-or-later
from os.path import join, dirname
import unittest
from bdd_dsl.utils.json import load_metamodels, process_bdd_us_from_graph
from bdd_dsl.models.frames import (
    FR_CRITERIA,
    FR_SCENARIO,
    FR_GIVEN,
    FR_THEN,
    FR_CLAUSES,
    FR_CLAUSES_DATA,
)
from bdd_dsl.utils.jinja import (
    create_given_clauses_strings,
    create_then_clauses_strings,
    prepare_gherkin_feature_data,
)

PKG_ROOT = join(dirname(__file__), "..")
META_MODELs_PATH = join(PKG_ROOT, "metamodels")
MODELS_PATH = join(PKG_ROOT, "models")


class BDD(unittest.TestCase):
    def setUp(self):
        self.graph = load_metamodels()
        self.graph.parse(
            join(MODELS_PATH, "acceptance-criteria", "bdd", "templates", "pickup.json"),
            format="json-ld",
        )
        self.graph.parse(
            join(MODELS_PATH, "acceptance-criteria", "bdd", "pickup-variants.json"),
            format="json-ld",
        )
        self.graph.parse(join(MODELS_PATH, "environments", "brsu.json"), format="json-ld")
        self.graph.parse(join(MODELS_PATH, "environments", "avl.json"), format="json-ld")
        self.graph.parse(join(MODELS_PATH, "agents", "brsu.json"), format="json-ld")

    def test_bdd(self):
        bdd_result = process_bdd_us_from_graph(self.graph)
        self.assertIsInstance(bdd_result, list)
        for us_data in bdd_result:
            prepare_gherkin_feature_data(us_data)

            for scenario_data in us_data[FR_CRITERIA]:
                given_clause_strings = create_given_clauses_strings(
                    scenario_data[FR_SCENARIO][FR_GIVEN][FR_CLAUSES], us_data[FR_CLAUSES_DATA]
                )
                self.assertTrue(len(given_clause_strings) > 0)
                self.assertTrue(len(given_clause_strings) == len(scenario_data["given_clauses"]))
                then_clause_strings = create_then_clauses_strings(
                    scenario_data[FR_SCENARIO][FR_THEN][FR_CLAUSES], us_data[FR_CLAUSES_DATA]
                )
                self.assertTrue(len(then_clause_strings) > 0)
                self.assertTrue(len(then_clause_strings) == len(scenario_data["then_clauses"]))


if __name__ == "__main__":
    unittest.main()
