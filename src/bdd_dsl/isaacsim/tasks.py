# SPDX-License-Identifier:  TODO
import numpy as np
from typing import Optional

# These imports are assumed to be called after SimulationApp() call, otherwise my cause import errors
from bdd_dsl.isaacsim.utils import get_asset_path, get_asset_physics
from omni.isaac.core.tasks import BaseTask
from omni.isaac.core.scenes.scene import Scene
from omni.isaac.core.objects import DynamicCuboid
from omni.isaac.core.utils.prims import is_prim_path_valid
from omni.isaac.core.prims.rigid_prim import RigidPrim
from omni.isaac.core.utils.stage import add_reference_to_stage, get_stage_units
from omni.isaac.core.utils.string import find_unique_string_name
from omni.isaac.franka import Franka


class PickPlace(BaseTask):
    """[summary]

    Expected scenario information (some maybe generated):
    - objects:
        - models:
            - resource mapping
        - instances:
            - model mapping
            - initial pose
            - initial configuration?
    - workspaces:
        - object instance mapping, e.g. table
    - agents:
        - models
        - instances:
            - model mapping
            - initial pose
            - initial configuration
            - control/actuation interface?

    Expected task information:
    - target object
    - target workspace

    Expected measurements
    - distance between target object and robot end-effector
    - distance between target object and place location

    Args:
        name (str): [description]
        cube_initial_position (Optional[np.ndarray], optional): [description]. Defaults to None.
        cube_initial_orientation (Optional[np.ndarray], optional): [description]. Defaults to None.
        target_position (Optional[np.ndarray], optional): [description]. Defaults to None.
        cube_size (Optional[np.ndarray], optional): [description]. Defaults to None.
        offset (Optional[np.ndarray], optional): [description]. Defaults to None.
    """

    def __init__(
        self,
        name: str,
        scenario_info: dict,
        cube_initial_position: Optional[np.ndarray] = None,
        cube_initial_orientation: Optional[np.ndarray] = None,
        target_position: Optional[np.ndarray] = None,
        cube_size: Optional[np.ndarray] = None,
        offset: Optional[np.ndarray] = None,
    ) -> None:
        BaseTask.__init__(self, name=name, offset=offset)
        self._robot = None
        self._scenario_info = scenario_info
        self._target_cube = None
        self._cube = None
        self._cube_initial_position = cube_initial_position
        self._cube_initial_orientation = cube_initial_orientation
        self._target_position = target_position
        self._cube_size = cube_size
        if self._cube_size is None:
            self._cube_size = np.array([0.0515, 0.0515, 0.0515]) / get_stage_units()
        if self._cube_initial_position is None:
            self._cube_initial_position = np.array([0.3, 0.3, 0.3]) / get_stage_units()
        if self._cube_initial_orientation is None:
            self._cube_initial_orientation = np.array([1, 0, 0, 0])
        if self._target_position is None:
            self._target_position = np.array([-0.3, -0.3, 0]) / get_stage_units()
            self._target_position[2] = self._cube_size[2] / 2.0
        self._target_position = self._target_position + self._offset
        return

    def set_up_scene(self, scene: Scene) -> None:
        """[summary]

        Args:
            scene (Scene): [description]
        """
        super().set_up_scene(scene)
        scene.add_default_ground_plane()
        cube_prim_path = find_unique_string_name(
            initial_name="/World/Cube", is_unique_fn=lambda x: not is_prim_path_valid(x)
        )
        cube_name = find_unique_string_name(
            initial_name="cube", is_unique_fn=lambda x: not self.scene.object_exists(x)
        )
        self._cube = scene.add(
            DynamicCuboid(
                name=cube_name,
                position=self._cube_initial_position,
                orientation=self._cube_initial_orientation,
                prim_path=cube_prim_path,
                scale=self._cube_size,
                size=1.0,
                color=np.array([0, 0, 1]),
            )
        )
        for instance_info in self._scenario_info["objects"]["instances"]:
            model_id = instance_info["model"]
            model_info = self._scenario_info["objects"]["models"][model_id]
            asset_path = get_asset_path(**model_info)
            instance_prim_path = find_unique_string_name(
                initial_name="/World/Objects/" + model_id, is_unique_fn=lambda x: not is_prim_path_valid(x)
            )
            instance_name = find_unique_string_name(
                initial_name=model_id, is_unique_fn=lambda x: not self.scene.object_exists(x)
            )
            add_reference_to_stage(usd_path=asset_path, prim_path=instance_prim_path)
            initial_position = None
            if "initial_postion" in instance_info:
                initial_position = np.array(instance_info["initial_postion"]) / get_stage_units()
            obj_instance = scene.add(
                RigidPrim(
                    prim_path=instance_prim_path,
                    name=instance_name,
                    position=initial_position,
                    orientation=self._cube_initial_orientation,
                    # scale=np.array([0.2, 0.2, 0.2]) / get_stage_units(),
                    **get_asset_physics(model_info["asset_id"])
                )
            )
            self._task_objects[obj_instance.name] = obj_instance

        self._task_objects[self._cube.name] = self._cube
        self._robot = self.set_robot()
        scene.add(self._robot)
        self._task_objects[self._robot.name] = self._robot
        self._move_task_objects_to_their_frame()
        return

    def set_robot(self) -> Franka:
        """[summary]

        Returns:
            Franka: [description]
        """
        franka_prim_path = find_unique_string_name(
            initial_name="/World/Franka", is_unique_fn=lambda x: not is_prim_path_valid(x)
        )
        franka_robot_name = find_unique_string_name(
            initial_name="my_franka", is_unique_fn=lambda x: not self.scene.object_exists(x)
        )
        return Franka(prim_path=franka_prim_path, name=franka_robot_name)

    def set_params(
        self,
        cube_position: Optional[np.ndarray] = None,
        cube_orientation: Optional[np.ndarray] = None,
        target_position: Optional[np.ndarray] = None,
    ) -> None:
        if target_position is not None:
            self._target_position = target_position
        if cube_position is not None or cube_orientation is not None:
            self._cube.set_local_pose(translation=cube_position, orientation=cube_orientation)
        return

    def get_params(self) -> dict:
        params_representation = {}
        position, orientation = self._cube.get_local_pose()
        params_representation["cube_position"] = {"value": position, "modifiable": True}
        params_representation["cube_orientation"] = {"value": orientation, "modifiable": True}
        params_representation["target_position"] = {
            "value": self._target_position,
            "modifiable": True,
        }
        params_representation["cube_name"] = {"value": self._cube.name, "modifiable": False}
        params_representation["robot_name"] = {"value": self._robot.name, "modifiable": False}
        return params_representation

    def get_observations(self) -> dict:
        """[summary]

        Returns:
            dict: [description]
        """
        joints_state = self._robot.get_joints_state()
        cube_position, cube_orientation = self._cube.get_local_pose()
        end_effector_position, _ = self._robot.end_effector.get_local_pose()
        return {
            self._cube.name: {
                "position": cube_position,
                "orientation": cube_orientation,
                "target_position": self._target_position,
            },
            self._robot.name: {
                "joint_positions": joints_state.positions,
                "end_effector_position": end_effector_position,
            },
        }

    def pre_step(self, time_step_index: int, simulation_time: float) -> None:
        """[summary]

        Args:
            time_step_index (int): [description]
            simulation_time (float): [description]
        """
        return

    def post_reset(self) -> None:
        from omni.isaac.manipulators.grippers.parallel_gripper import ParallelGripper

        if isinstance(self._robot.gripper, ParallelGripper):
            self._robot.gripper.set_joint_positions(self._robot.gripper.joint_opened_positions)
        return

    def calculate_metrics(self) -> dict:
        """[summary]"""
        raise NotImplementedError

    def is_done(self) -> bool:
        """[summary]"""
        raise NotImplementedError
