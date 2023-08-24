# SPDX-License-Identifier:  TODO
from enum import IntEnum

from bdd_dsl.utils.common import check_or_convert_ndarray


_YCB_PATH = "/Isaac/Props/YCB"
_ISAAC_ASSETS = {
    "ycb_cracker": {
        "path": f"{_YCB_PATH}/Axis_Aligned_Physics/003_cracker_box.usd",
        "configs": {"mass": 0.411},
    },
    "ycb_sugar": {
        "path": f"{_YCB_PATH}/Axis_Aligned_Physics/004_sugar_box.usd",
        "configs": {"mass": 0.514},
    },
    "ycb_soup": {
        "path": f"{_YCB_PATH}/Axis_Aligned_Physics/005_tomato_soup_can.usd",
        "configs": {"mass": 0.349},
    },
    "ycb_mustard": {
        "path": f"{_YCB_PATH}/Axis_Aligned_Physics/006_mustard_bottle.usd",
        "configs": {"mass": 0.603},
    },
}
_CACHED_ASSET_ROOT = None
_CACHED_SHAPE_MAP = None


class PathType(IntEnum):
    ISAAC_SIM_PATH = 0
    SYSTEM_PATH = 1


class SimpleShape(IntEnum):
    CUBOID = 0
    CYLINDER = 1
    SPHERE = 2
    CONE = 3
    CAPSULE = 4


class ModelType(IntEnum):
    SIMPLE_SHAPE = 0
    USD = 1


def get_assets_root_path_or_die() -> str:
    """Raise exception if asset root directory can't be found.

    Raises:
        RuntimeError: if asset root directory can't befound

    Returns:
        str: Root directory containing assets from Isaac Sim
    """
    global _CACHED_ASSET_ROOT
    if _CACHED_ASSET_ROOT is not None:
        return _CACHED_ASSET_ROOT

    # These imports are assumed to be called after SimulationApp() call, otherwise my cause import errors
    from omni.isaac.core.utils.nucleus import get_assets_root_path

    _CACHED_ASSET_ROOT = get_assets_root_path()
    if _CACHED_ASSET_ROOT is not None:
        return _CACHED_ASSET_ROOT

    raise RuntimeError("Could not find Isaac Sim assets folder")


def get_isaacsim_asset_path_by_id(asset_name: str) -> str:
    """Get path for known Isaac Sim assets

    Args:
        asset_name (str): name of asset

    Raises:
        RuntimeError: if asset is not known

    Returns:
        str: path to requested asset
    """
    if asset_name not in _ISAAC_ASSETS:
        raise RuntimeError(f"Asset with name '{asset_name}' not on record")

    return get_assets_root_path_or_die() + _ISAAC_ASSETS[asset_name]["path"]


def get_asset_path(path_type: PathType, path: str = None, asset_id: str = None, **kwargs) -> str:
    if path_type == PathType.ISAAC_SIM_PATH:
        if asset_id is not None:
            return get_isaacsim_asset_path_by_id(asset_id)
        if path is not None:
            return get_assets_root_path_or_die() + path
        raise RuntimeError(
            f"'get_asset_path' called for path type '{str(path_type)}' without specifying 'asset_id' or 'path'"
        )

    if path_type == PathType.SYSTEM_PATH:
        if path is not None:
            return path
        raise RuntimeError(
            f"'get_asset_path' called for path type '{str(path_type)}' without specifying 'path'"
        )

    raise RuntimeError(f"unhandled path type: {str(path_type)}")


def get_asset_configs(asset_name: str) -> dict:
    if asset_name not in _ISAAC_ASSETS:
        return {}

    return _ISAAC_ASSETS[asset_name]["configs"]


def create_simple_shape_in_scene(
    scene, shape: SimpleShape, instance_name: str, instance_prim_path: str, prim_configs: dict
):
    from omni.isaac.core.objects import (
        DynamicCuboid,
        DynamicSphere,
        DynamicCylinder,
        DynamicCone,
        DynamicCapsule,
    )

    global _CACHED_SHAPE_MAP
    if _CACHED_SHAPE_MAP is None:
        _CACHED_SHAPE_MAP = {
            SimpleShape.CUBOID: DynamicCuboid,
            SimpleShape.SPHERE: DynamicSphere,
            SimpleShape.CYLINDER: DynamicCylinder,
            SimpleShape.CONE: DynamicCone,
            SimpleShape.CAPSULE: DynamicCapsule,
        }

    if shape not in _CACHED_SHAPE_MAP:
        raise RuntimeError(f"can't create shape for unhandled shape type '{str(shape)}'")

    shape_class = _CACHED_SHAPE_MAP[shape]
    return scene.add(
        shape_class(
            name=instance_name,
            prim_path=instance_prim_path,
            **prim_configs,
        )
    )


def create_rigid_prim_in_scene(
    scene,
    instance_name: str,
    prim_prefix: str,
    model_info: dict,
    instance_configs: dict,
):
    from omni.isaac.core.utils.prims import is_prim_path_valid
    from omni.isaac.core.utils.stage import add_reference_to_stage, get_stage_units
    from omni.isaac.core.utils.string import find_unique_string_name
    from omni.isaac.core.prims.rigid_prim import RigidPrim

    instance_prim_path = find_unique_string_name(
        initial_name=prim_prefix + instance_name,
        is_unique_fn=lambda x: not is_prim_path_valid(x),
    )
    instance_name = find_unique_string_name(
        initial_name=instance_name,
        is_unique_fn=lambda x: not scene.object_exists(x),
    )

    prim_configs = {}
    model_type = model_info["type"]
    if model_type == ModelType.USD:
        if "asset_id" in model_info:
            # add configs from known models in ISAAC Sim assets
            prim_configs.update(get_asset_configs(model_info["asset_id"]))

    # add instance configs
    if "initial_position" in instance_configs:
        prim_configs["position"] = (
            check_or_convert_ndarray(instance_configs["initial_position"]) / get_stage_units()
        )
    if "initial_orientation" in instance_configs:
        prim_configs["orientation"] = check_or_convert_ndarray(
            instance_configs["initial_orientation"]
        )
    if "scale" in instance_configs:
        prim_configs["scale"] = (
            check_or_convert_ndarray(instance_configs["scale"]) / get_stage_units()
        )
    if "color" in instance_configs:
        prim_configs["color"] = (
            check_or_convert_ndarray(instance_configs["color"]) / get_stage_units()
        )

    if model_type == ModelType.USD:
        asset_path = get_asset_path(**model_info)
        add_reference_to_stage(usd_path=asset_path, prim_path=instance_prim_path)
        return scene.add(
            RigidPrim(prim_path=instance_prim_path, name=instance_name, **prim_configs)
        )

    if model_type == ModelType.SIMPLE_SHAPE:
        shape = model_info["shape"]
        return create_simple_shape_in_scene(
            scene, shape, instance_name, instance_prim_path, prim_configs
        )

    raise RuntimeError("unhandled object model type: " + str(model_type))
