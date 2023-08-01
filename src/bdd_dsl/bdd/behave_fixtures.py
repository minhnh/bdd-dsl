# SPDX-License-Identifier:  GPL-3.0-or-later
import time
import multiprocessing
import logging
from behave import fixture
from behave.runner import Context
from bdd_dsl.events.zmq import ZmqEventServer, ZmqEventClient
from bdd_dsl.exception import GracefulExit
from bdd_dsl.behaviours.robosuite import SimulatedScenario
from bdd_dsl.utils.json import create_event_handler_from_data, create_subtree_behaviours
from bdd_dsl.models.frames import FR_NAME, FR_EVENTS


def zmq_event_server_process(**kwargs):
    event_names = kwargs.get("event_names", list())
    if not event_names:
        raise ValueError("'event_names' not specified or empty list of events")
    hostname = kwargs.get("hostname", "*")
    port = kwargs.get("port", 5555)
    sleep_time = kwargs.get("sleep_time", 0.01)
    server = ZmqEventServer(id, event_names, hostname=hostname, port=port)

    while True:
        try:
            server.handle_request()
            time.sleep(sleep_time)
        except GracefulExit as e:
            logging.info(f"zmq_event_server_process: terminating with signum '{e.signum}'")
            break


@fixture
def setup_event_server(context: Context, *args, **kwargs):
    kwargs["event_names"] = [event[FR_NAME] for event in context.event_data[FR_EVENTS]]
    try:
        event_server_process = multiprocessing.Process(
            target=zmq_event_server_process, kwargs=kwargs
        )
        event_server_process.start()
        context.add_cleanup(event_server_process.terminate)
    except GracefulExit as e:
        logging.info(f"setup_event_server: terminating with signum '{e.signum}'")


def sim_execution_process(**kwargs):
    hostname = kwargs.get("hostname", "localhost")
    port = kwargs.get("port", 5555)
    event_data = kwargs.get("event_data")
    event_handler = create_event_handler_from_data(
        event_data, ZmqEventClient, {"hostname": hostname, "port": port}
    )
    bt_root_node = create_subtree_behaviours(kwargs.get("bt_root_data"), event_handler)
    pickup_scenario = SimulatedScenario(
        event_handler,
        bt_root_node,
        rendering=False,
        env_name="PickPlace",
        robots=["Panda"],
        bt_root_name="bt/pickup-single-arm-rs",
        e_handler_cls=ZmqEventClient,
        e_handler_kwargs={"hostname": hostname, "port": port},
    )
    pickup_scenario.setup(target_object="Milk", timeout=15)
    done = False
    while not done:
        try:
            done = pickup_scenario.step()
        except GracefulExit as e:
            pickup_scenario.interrupt()
            logging.info(f"sim_execution_process: terminating with signum '{e.signum}'")
            break


@fixture
def setup_sim(context: Context, *args, **kwargs):
    kwargs["event_data"] = context.event_data
    kwargs["bt_root_data"] = context.bt_root_data
    try:
        sim_process = multiprocessing.Process(target=sim_execution_process, kwargs=kwargs)
        sim_process.start()
        context.add_cleanup(sim_process.terminate)
    except GracefulExit as e:
        logging.info(f"setup_event_server: terminating with signum '{e.signum}'")
