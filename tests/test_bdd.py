# SPDX-License-Identifier:  GPL-3.0-or-later
import unittest
import rdflib
from rdf_utils.resolver import install_resolver
from rdf_utils.uri import URL_SECORO_M
from bdd_dsl.models.user_story import UserStoryLoader
from bdd_dsl.models.frames import FR_CRITERIA, FR_VARIABLES, FR_VARIATIONS
from bdd_dsl.utils.jinja import prepare_jinja2_template_data

MODEL_URLS = {
    f"{URL_SECORO_M}/acceptance-criteria/bdd/environments/secorolab.env.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/agents/isaac-sim.agn.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/scenes/secorolab-env.scene.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/scenes/isaac-agents.scene.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/templates/pickplace.tmpl.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/pickplace-secorolab-isaac.var.json": "json-ld",
}


class BDDTest(unittest.TestCase):
    def setUp(self):
        install_resolver()
        self.graph = rdflib.ConjunctiveGraph()
        for url, fmt in MODEL_URLS.items():
            self.graph.parse(url, format=fmt)

    def test_bdd(self):
        us_loader = UserStoryLoader(self.graph)
        processed_bdd_data = prepare_jinja2_template_data(us_loader, self.graph)
        for us_data in processed_bdd_data:
            for scenario_data in us_data[FR_CRITERIA]:
                self.assertTrue(len(scenario_data["given_clauses"]) > 0)
                self.assertTrue(len(scenario_data["then_clauses"]) > 0)
                self.assertTrue(len(scenario_data[FR_VARIABLES]) > 0)
                self.assertTrue(len(scenario_data[FR_VARIATIONS]) > 0)
                self.assertTrue(
                    len(scenario_data[FR_VARIATIONS][0]) == len(scenario_data[FR_VARIABLES])
                )


if __name__ == "__main__":
    unittest.main()
