# SPDX-License-Identifier:  GPL-3.0-or-later
from os.path import join, dirname
import unittest
from py_trees.trees import BehaviourTree
from bdd_dsl.events.event_handler import SimpleEventLoop
from bdd_dsl.utils.json import (
    load_metamodels,
    create_event_handler_from_graph,
    create_bt_from_graph,
)


PKG_ROOT = join(dirname(__file__), "..")
META_MODELs_PATH = join(PKG_ROOT, "metamodels")
MODELS_PATH = join(PKG_ROOT, "models")


class NominalCoordination(unittest.TestCase):
    def setUp(self):
        self.graph = load_metamodels()
        self.event_loop_model_file = join(MODELS_PATH, "coordination", "pickup-events.json")
        self.graph.parse(self.event_loop_model_file, format="json-ld")
        self.graph.parse(
            join(MODELS_PATH, "coordination", "bt", "pickup-behaviours.json"), format="json-ld"
        )
        self.graph.parse(
            join(MODELS_PATH, "coordination", "bt", "pickup-dual-arm-behaviours.json"),
            format="json-ld",
        )

    def test_event_loop(self):
        event_loops = create_event_handler_from_graph(self.graph, SimpleEventLoop, {})
        self.assertTrue(
            len(event_loops) > 0,
            f"no event loop created from '{self.event_loop_model_file}'",
        )

        for el in event_loops:
            self.assertTrue(len(el.event_data) > 0, f"no event created for '{el.id}'")

            for e_name in el.event_data:
                self.assertFalse(el.consume(e_name), f"event not initialized to 'False': {e_name}")
                el.produce(e_name)

            # trigger event value update
            el.reconfigure()

            for e_name in el.event_data:
                self.assertTrue(
                    el.consume(e_name),
                    f"event not set to 'True' after reconfigure: {e_name}",
                )

    def test_behaviour_tree(self):
        els_and_bts = create_bt_from_graph(self.graph, bt_name="bt/bogus-invalid-name")
        num_result = len(els_and_bts)
        self.assertEqual(num_result, 0, f"expect no result for invalid name, got {num_result}")
        els_and_bts = create_bt_from_graph(self.graph, bt_name="bt/pickup-dual-arm-mockup")
        num_result = len(els_and_bts)
        self.assertEqual(num_result, 1, f"expect exactly 1 result, got {num_result}")
        el, bt_root = els_and_bts[0]
        bt = BehaviourTree(bt_root)
        el.reconfigure()
        bt.tick()


if __name__ == "__main__":
    unittest.main()
