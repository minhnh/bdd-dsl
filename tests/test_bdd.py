# SPDX-License-Identifier:  GPL-3.0-or-later
import unittest
import rdflib
from bdd_dsl.utils.json import process_bdd_us_from_graph
from rdf_utils.resolver import install_resolver
from bdd_dsl.models.uri import URL_SECORO_M
from bdd_dsl.models.frames import (
    FR_CRITERIA,
    FR_SCENARIO,
    FR_GIVEN,
    FR_THEN,
    FR_CLAUSES_DATA,
)
from bdd_dsl.utils.jinja import (
    create_given_clauses_strings,
    create_then_clauses_strings,
    prepare_gherkin_feature_data,
)

MODEL_URLS = {
    f"{URL_SECORO_M}/acceptance-criteria/bdd/environments/secorolab.env.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/agents/isaac-sim.agn.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/scenes/secorolab-env.scene.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/scenes/isaac-agents.scene.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/templates/pickplace.tmpl.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/pickplace-secorolab-isaac.var.json": "json-ld",
}


class BDD(unittest.TestCase):
    def setUp(self):
        install_resolver()
        self.graph = rdflib.ConjunctiveGraph()
        for url, fmt in MODEL_URLS.items():
            self.graph.parse(url, format=fmt)

    def test_bdd(self):
        bdd_result = process_bdd_us_from_graph(self.graph, timeout=10)
        self.assertIsInstance(bdd_result, list)
        for us_data in bdd_result:
            prepare_gherkin_feature_data(us_data)

            for scenario_data in us_data[FR_CRITERIA]:
                given_clause_strings = create_given_clauses_strings(
                    scenario_data[FR_SCENARIO][FR_GIVEN], us_data[FR_CLAUSES_DATA]
                )
                self.assertTrue(len(given_clause_strings) > 0)
                self.assertTrue(len(given_clause_strings) == len(scenario_data["given_clauses"]))
                then_clause_strings = create_then_clauses_strings(
                    scenario_data[FR_SCENARIO][FR_THEN], us_data[FR_CLAUSES_DATA]
                )
                self.assertTrue(len(then_clause_strings) > 0)
                self.assertTrue(len(then_clause_strings) == len(scenario_data["then_clauses"]))


if __name__ == "__main__":
    unittest.main()
