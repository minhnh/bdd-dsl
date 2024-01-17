from bdd_dsl.isaacsim.utils import ModelType, PathType, SimpleShape
from bdd_dsl.utils.common import get_valid_var_name
from bdd_dsl.utils.json import get_pose_coordinates
from bdd_dsl.models.frames import FR_POSE, FR_WRT, FR_NAME, FR_POSITION, FR_ORIENTATION

from behave import given


# TODO(minhnh) replace with JSON model
OBJECT_MODEL_MAPS = {
    "models": {
        "cracker": {
            "type": ModelType.USD,
            "path_type": PathType.ISAAC_SIM_PATH,
            "asset_id": "ycb_cracker",
        },
        "soup": {
            "type": ModelType.USD,
            "path_type": PathType.ISAAC_SIM_PATH,
            "asset_id": "ycb_soup",
        },
        "sugar": {
            "type": ModelType.USD,
            "path_type": PathType.ISAAC_SIM_PATH,
            "asset_id": "ycb_sugar",
        },
        "mustard": {
            "type": ModelType.USD,
            "path_type": PathType.ISAAC_SIM_PATH,
            "asset_id": "ycb_mustard",
        },
        "chips": {
            "type": ModelType.USD,
            "path_type": PathType.SYSTEM_PATH,
            "path": "/media/ext4-data/user-data/mnguy2m/imported-usd/ycb/001_chips_can-tsdf.usd",
        },
        "ball": {"type": ModelType.SIMPLE_SHAPE, "shape": SimpleShape.SPHERE},
        "block": {"type": ModelType.SIMPLE_SHAPE, "shape": SimpleShape.CUBOID},
        "battery": {"type": ModelType.SIMPLE_SHAPE, "shape": SimpleShape.CYLINDER},
    },
    "model-map": {
        # {"id": "cracker_box", "model_id": "cracker", "configs": {"initial_position": [0.1, 0.1, 0.2]}},
        "env:brsu/bottle": {
            "model_id": "mustard",
            "configs": {"initial_position": [0.2, -0.1, 0.2]},
        },
        "env:brsu/box": {"model_id": "sugar", "configs": {"initial_position": [0.2, 0.2, 0.2]}},
        "env:brsu/ball": {
            "model_id": "ball",
            "configs": {
                "initial_position": [0.3, 0.3, 0.05],
                "scale": [0.0315, 0.0315, 0.0315],
                "size": 1.0,
                "color": [1, 0, 1],
            },
        },
        "block": {
            "model_id": "block",
            "configs": {
                "initial_position": [0.3, 0.1, 0.05],
                "scale": [0.0515, 0.0515, 0.0515],
                "size": 1.0,
                "color": [0, 1, 1],
            },
        },
        "env:avl/cylindrical1": {
            "model_id": "battery",
            "configs": {
                "initial_position": [0.3, -0.3, 0.05],
                "scale": [0.0315, 0.0315, 0.0515],
                "size": 1.0,
                "color": [0, 1, 1],
            },
        },
        # {"id": "chips", "model_id": "chips", "configs": {"initial_position": [0.2, -0.1, 0.2]}}
    },
}


@given("a set of objects")
def step_add_objects(context):
    context.objects.clear()
    for row in context.table:
        obj_id = row["name"]
        if obj_id not in OBJECT_MODEL_MAPS["model-map"]:
            raise RuntimeError(f"no model mapping for object ID '{obj_id}'")
        model_id = OBJECT_MODEL_MAPS["model-map"][obj_id]["model_id"]
        valid_obj_id = get_valid_var_name(obj_id)
        context.objects[valid_obj_id] = OBJECT_MODEL_MAPS["model-map"][obj_id]
        if model_id not in OBJECT_MODEL_MAPS["models"]:
            raise RuntimeError(f"no model with ID '{model_id}'")
        context.objects[valid_obj_id]["model_info"] = OBJECT_MODEL_MAPS["models"][model_id]

        if obj_id in context.obj_pose_data:
            obj_data = context.obj_pose_data[obj_id]
            for _, pose_data in obj_data[FR_POSE].items():
                if "world-frame" not in pose_data[FR_WRT][FR_NAME]:
                    continue
                coords = get_pose_coordinates(pose_data)
                context.objects[valid_obj_id]["configs"]["initial_position"] = coords[FR_POSITION]
                context.objects[valid_obj_id]["configs"]["initial_orientation"] = coords[
                    FR_ORIENTATION
                ]


@given("specified objects, workspaces and agents are available")
def step_create_world(context):
    from bdd_dsl.isaacsim.tasks import PickPlace
    from omni.isaac.franka.controllers import PickPlaceController

    context.world.clear()

    scenario_info = {"objects": context.objects}
    context.task = PickPlace(name="franka_pick_place", scenario_info=scenario_info)

    context.world.add_task(context.task)
    context.world.reset()
    task_params = context.task.get_params()
    context.robot = context.world.scene.get_object(task_params["robot_name"]["value"])
    context.behaviour = PickPlaceController(
        name="pick_place_controller",
        gripper=context.robot.gripper,
        robot_articulation=context.robot,
    )
    context.controller = context.robot.get_articulation_controller()

    context.world.reset()
    context.behaviour.reset()


@given('"{templates_pick_object}" is located at "{templates_pick_workspace}"')
def is_located_at(context, templates_pick_object, templates_pick_workspace):
    valid_obj_id = get_valid_var_name(templates_pick_object)
    assert valid_obj_id in context.task.pickable_objects
    context.task.set_params(target_object=valid_obj_id)
