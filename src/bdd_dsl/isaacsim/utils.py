# SPDX-License-Identifier:  TODO
from enum import IntEnum

# These imports are assumed to be called after SimulationApp() call, otherwise my cause import errors
from omni.isaac.core.utils.nucleus import get_assets_root_path


_YCB_PATH = "/Isaac/Props/YCB"
_KNOWN_ASSET_PATHS = {
    "ycb_cracker": f"{_YCB_PATH}/Axis_Aligned_Physics/003_cracker_box.usd",
    "ycb_sugar": f"{_YCB_PATH}/Axis_Aligned_Physics/004_sugar_box.usd",
    "ycb_soup": f"{_YCB_PATH}/Axis_Aligned_Physics/005_tomato_soup_can.usd",
    "ycb_mustard": f"{_YCB_PATH}/Axis_Aligned_Physics/006_mustard_bottle.usd",
}
_KNOWN_PHYSICS = {
    "ycb_cracker": {"mass": 0.411},
    "ycb_sugar": {"mass": 0.514},
    "ycb_soup": {"mass": 0.349},
    "ycb_mustard": {"mass": 0.603},
}
_CACHED_ASSET_ROOT = None


class PathType(IntEnum):
    ISAAC_SIM_PATH = 0
    SYSTEM_PATH = 1


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
    if asset_name not in _KNOWN_ASSET_PATHS:
        raise RuntimeError(f"Asset with name '{asset_name}' not on record")

    return get_assets_root_path_or_die() + _KNOWN_ASSET_PATHS[asset_name]


def get_asset_path(**kwargs) -> str:
    path_type = kwargs.get("path_type", None)
    path = kwargs.get("path", None)
    asset_id = kwargs.get("asset_id", None)
    if path_type == PathType.ISAAC_SIM_PATH:
        if id is not None:
            return get_isaacsim_asset_path_by_id(asset_id)
        if path is not None:
            return get_assets_root_path_or_die() + path
        raise RuntimeError(
            f"'get_asset' called for path type '{str(path_type)}' without 'id' or 'path' in kwargs"
        )

    if path_type == PathType.SYSTEM_PATH:
        if path is not None:
            return path
        raise RuntimeError(
            f"'get_asset' called for path type '{str(path_type)}' without 'path' in kwargs"
        )

    raise RuntimeError(f"unhandled path type: {str(path_type)}")


def get_asset_physics(asset_name: str) -> dict:
    if asset_name not in _KNOWN_PHYSICS:
        return {}

    return _KNOWN_PHYSICS[asset_name]
