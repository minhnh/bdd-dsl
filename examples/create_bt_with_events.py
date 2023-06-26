from os.path import join, dirname

# import py_trees as pt
# from pprint import pprint
from bdd_dsl.utils.json import (
    load_metamodels,
    create_bt_from_graph,
    create_event_handler_from_data,
    get_bt_event_data_from_graph,
    create_subtree_behaviours,
)
from bdd_dsl.behaviours.robosuite import SimulatedScenario
from bdd_dsl.events.zmq import ZmqEventClient


PKG_ROOT = join(dirname(__file__), "..")
MODELS_PATH = join(PKG_ROOT, "models")
BT_ROOT_NAME = "bt/pickup-single-arm-rs"
CLIENT_HOSTNAME = "localhost"
PORT = 5555


def main():
    g = load_metamodels()
    g.parse(join(MODELS_PATH, "coordination", "pickup-events.json"), format="json-ld")
    g.parse(join(MODELS_PATH, "coordination", "bt", "pickup-behaviours.json"), format="json-ld")
    g.parse(
        join(MODELS_PATH, "coordination", "bt", "pickup-dual-arm-behaviours.json"), format="json-ld"
    )

    els_and_bts = create_bt_from_graph(g)
    for el, bt in els_and_bts:
        print(f"found behaviour tree '{bt.name}' associated with event loop '{el.id}'")
        # pprint(el.event_data)

    # selected_el, selected_bt_root = els_and_bts[0]
    # pt.display.render_dot_tree(selected_bt_root)
    e_data_and_bts = get_bt_event_data_from_graph(g, BT_ROOT_NAME)
    if len(e_data_and_bts) != 1:
        raise ValueError(
            f"expected 1 result for behaviour tree '{BT_ROOT_NAME}', got: {len(e_data_and_bts)}"
        )
    event_data = e_data_and_bts[0][0]
    bt_root_data = e_data_and_bts[0][1]

    event_handler = create_event_handler_from_data(
        event_data, ZmqEventClient, {"hostname": CLIENT_HOSTNAME, "port": PORT}
    )
    bt_root_node = create_subtree_behaviours(bt_root_data, event_handler)
    pickup_scenario = SimulatedScenario(
        event_handler,
        bt_root_node,
        rendering=True,
        env_name="PickPlace",
        robots=["Panda"],
    )
    pickup_scenario.setup(target_object="Milk", timeout=15)

    done = False
    while not done:
        try:
            done = pickup_scenario.step()
        except KeyboardInterrupt:
            pickup_scenario.interrupt()
            break
    print("scenario completed")


if __name__ == "__main__":
    main()
