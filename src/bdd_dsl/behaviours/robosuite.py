# SPDX-License-Identifier:  GPL-3.0-or-later
import time
import numpy as np
import robosuite as rs
import py_trees as pt
from bdd_dsl.behaviours.actions import ActionWithEvents
from bdd_dsl.events.event_handler import EventHandler

# from pprint import pprint


class SimulatedScenario(object):
    def __init__(
        self,
        event_handler: EventHandler,
        bt_root,
        **kwargs,
    ):
        self.env = None
        self.target_object = None
        self.rendering = kwargs.get("rendering", True)

        self.event_loop = event_handler
        self.selected_bt_root = bt_root

        self.env_name = kwargs.get("env_name", "PickPlace")
        self.robots = kwargs.get("robots", ["Kinova3"])
        self.has_renderer = kwargs.get("has_renderer", True)
        self.has_offscreen_renderer = kwargs.get("has_offscreen_renderer", False)
        self.use_camera_obs = kwargs.get("use_camera_obs", False)

    def setup(self, **kwargs):
        self.target_object = kwargs.get("target_object", "Cereal")

        # choose OSC_POSE controller
        ctrl_configs = rs.load_controller_config(default_controller="OSC_POSITION")
        # pprint(ctrl_configs)

        # create environment instance
        self.env = rs.make(
            env_name=self.env_name,
            robots=self.robots,
            has_renderer=self.has_renderer,
            has_offscreen_renderer=self.has_offscreen_renderer,
            use_camera_obs=self.use_camera_obs,
            controller_configs=ctrl_configs,
        )

        # setup behaviour tree
        self.behaviour_tree = pt.trees.BehaviourTree(self.selected_bt_root)
        self.behaviour_tree.setup(**kwargs)

        # blackboard connections
        self.blackboard = pt.blackboard.Client(name=f"{self.behaviour_tree.root.name}_blackboard")
        self.blackboard.register_key(key="measurements", access=pt.common.Access.WRITE)
        self.blackboard.register_key(key="actions", access=pt.common.Access.READ)
        self.blackboard.register_key(key="target_object", access=pt.common.Access.WRITE)
        self.blackboard.target_object = self.target_object
        self.blackboard.measurements = self.env.reset()

    def step(self):
        self.behaviour_tree.tick()

        done = False
        try:
            # actions = np.random.randn(self.env.robots[0].dof)  # sample random action
            actions = self.blackboard.actions
            obs, reward, done, info = self.env.step(actions)  # take action in the environment
            # pprint(obs)
            self.blackboard.measurements = obs
        except KeyError:
            pass
        if self.rendering:
            self.env.render()  # render on display

        if done:
            self.interrupt()
        return done

    def interrupt(self):
        self.behaviour_tree.interrupt()
        self.env.close()


class MoveEndEffector(ActionWithEvents):
    def __init__(self, name, event_loop, start_event, end_event, **kwargs):
        super().__init__(name, event_loop, start_event, end_event)

        self._eef_distance_threshold = kwargs.get("distance_threshold", 0.05)  # in m
        self._eef_vel = kwargs.get("end_effector_speed", 0.35)  # in m/s
        self._period = kwargs.get("period", 0.01)  # in s

        self.blackboard = pt.blackboard.Client(name=f"{self.name}_blackboard")
        self.blackboard.register_key(key="target_object", access=pt.common.Access.READ)
        self.blackboard.register_key(key="measurements", access=pt.common.Access.READ)
        self.blackboard.register_key(key="actions", access=pt.common.Access.WRITE)

    def _initialise(self):
        self._begin_time = time.time()
        self.target_object = self.blackboard.target_object

    def _terminate(self, new_status):
        pass

    def update(self) -> pt.common.Status:
        try:
            measurements = self.blackboard.measurements
        except KeyError as e:
            self.logger.debug(e)
            return pt.common.Status.RUNNING

        obj_to_eef_pos = measurements[f"{self.target_object}_to_robot0_eef_pos"]
        if np.linalg.norm(obj_to_eef_pos) < self._eef_distance_threshold:
            self.logger.info(
                f"end-effector reached within '{self._eef_distance_threshold}' from object"
            )
            return pt.common.Status.SUCCESS

        current_time = time.time()
        if current_time - self._begin_time < self._period:
            return pt.common.Status.RUNNING

        self._begin_time = current_time
        # obj_position = measurements[f"{self.target_object}_pos"]
        # obj_quat = measurements[f"{self.target_object}_quat"]
        # target_pose = np.append(obj_position, obj_quat)
        # pprint(obj_to_eef_pos)
        self.blackboard.actions = np.append(-obj_to_eef_pos * self._eef_vel, 0)
        return pt.common.Status.RUNNING
