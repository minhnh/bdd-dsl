# SPDX-License-Identifier:  TODO
import numpy as np
from typing import Optional

from bdd_dsl.utils.common import check_or_convert_ndarray

# These imports are assumed to be called after SimulationApp() call, otherwise my cause import errors
from bdd_dsl.isaacsim.utils import create_rigid_prim_in_scene
from omni.isaac.core.tasks import BaseTask
from omni.isaac.core.scenes.scene import Scene
from omni.isaac.core.objects import DynamicCuboid
from omni.isaac.core.utils.prims import is_prim_path_valid
from omni.isaac.core.utils.stage import get_stage_units
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
        default_obj_position: Optional[np.ndarray] = None,
        default_obj_orientation: Optional[np.ndarray] = None,
        placing_position: Optional[np.ndarray] = None,
        cube_size: Optional[np.ndarray] = None,
        offset: Optional[np.ndarray] = None,
    ) -> None:
        BaseTask.__init__(self, name=name, offset=offset)
        self._robot = None
        self._scenario_info = scenario_info
        self._pickable_objects = set()
        self._target_object = None
        self._default_obj_position = default_obj_position
        self._default_obj_orientation = default_obj_orientation
        self._placing_position = placing_position
        self._cube_size = cube_size
        if self._cube_size is None:
            self._cube_size = np.array([0.0515, 0.0515, 0.0515]) / get_stage_units()
        if self._default_obj_position is None:
            self._default_obj_position = np.array([0.3, 0.3, 0.3]) / get_stage_units()
        if self._default_obj_orientation is None:
            self._default_obj_orientation = np.array([1, 0, 0, 0])
        if self._placing_position is None:
            self._placing_position = np.array([-0.3, -0.3, 0]) / get_stage_units()
            self._placing_position[2] = self._cube_size[2] / 2.0
        self._placing_position = self._placing_position + self._offset
        return

    def set_up_scene(self, scene: Scene) -> None:
        """[summary]

        Args:
            scene (Scene): [description]
        """
        super().set_up_scene(scene)
        scene.add_default_ground_plane()
        for instance_info in self._scenario_info["objects"]["instances"]:
            model_id = instance_info["model_id"]
            model_info = self._scenario_info["objects"]["models"][model_id]
            instance_configs = {
                "initial_position": self._default_obj_position,
                "initial_orientation": self._default_obj_orientation,
            }
            instance_configs.update(instance_info["configs"])
            obj_instance = create_rigid_prim_in_scene(
                scene,
                instance_name=instance_info["id"],
                prim_prefix="/World/Objects/",
                model_info=model_info,
                instance_configs=instance_configs,
            )
            self._task_objects[obj_instance.name] = obj_instance
            self._pickable_objects.add(obj_instance.name)

        self._robot = self.set_robot()
        scene.add(self._robot)
        self._task_objects[self._robot.name] = self._robot
        self._move_task_objects_to_their_frame()
        return

    @property
    def pickable_objects(self):
        return self._pickable_objects

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

    def set_params(self, **kwargs) -> None:
        """Set parameters values.

        Extension of BaseTask.set_params(). Modifiable parameters:
        - target_object: ID of object to be picked and placed
        - placing_position (np.ndarray): position to place the picked object. Defaults to None.

        Args:
            cube_position (Optional[np.ndarray], optional): _description_. Defaults to None.
            cube_orientation (Optional[np.ndarray], optional): _description_. Defaults to None.
        """
        placing_position = kwargs.get("placing_position", None)
        if placing_position is not None:
            self._placing_position = check_or_convert_ndarray(placing_position)

        target_object_id = kwargs.get("target_object", None)
        if target_object_id is not None:
            if target_object_id not in self._pickable_objects:
                raise ValueError(f"ID '{target_object_id}' not found among pickable objects.")
            self._target_object = target_object_id
        return

    def get_params(self) -> dict:
        """Return parameters values.

        Extension of BaseTask.get_params(). Parameters:
        - robot_name: name of robot
        - target_object: ID of object to be picked and placed
        - placing_position: position where the picked object should be placed

        Returns:
            dict: dictionary containing parameters' values and modifiable flag
        """
        params_representation = {}
        params_representation["robot_name"] = {"value": self._robot.name, "modifiable": False}
        params_representation["placing_position"] = {
            "value": self._placing_position,
            "modifiable": True,
        }
        params_representation["target_object"] = {"value": self._target_object, "modifiable": True}

        return params_representation

    def get_observations(self) -> dict:
        """[summary]

        Returns:
            dict: [description]
        """
        joints_state = self._robot.get_joints_state()
        if self._target_object is None:
            raise RuntimeError("no target object set")

        obj_position, obj_orientation = self._task_objects[self._target_object].get_local_pose()
        end_effector_position, _ = self._robot.end_effector.get_local_pose()
        return {
            "target_object": {
                "name": self._target_object,
                "position": obj_position,
                "orientation": obj_orientation,
                "placing_position": self._placing_position,
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
