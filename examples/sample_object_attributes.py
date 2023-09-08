from os.path import join, dirname
from bdd_dsl.utils.json import load_metamodels, get_object_poses
from pprint import pprint


PKG_ROOT = join(dirname(__file__), "..")
MODELS_PATH = join(PKG_ROOT, "models")


def main():
    g = load_metamodels()
    g.parse(
        join(MODELS_PATH, "simulation", "isaac-pickup.json"),
        format="json-ld",
    )
    g.parse(
        join(MODELS_PATH, "simulation", "pickup.geom.json"),
        format="json-ld",
    )
    g.parse(join(MODELS_PATH, "environments", "brsu.json"), format="json-ld")
    g.parse(join(MODELS_PATH, "environments", "brsu.geom.json"), format="json-ld")
    g.parse(join(MODELS_PATH, "environments", "avl.json"), format="json-ld")
    g.parse(join(MODELS_PATH, "environments", "avl.geom.json"), format="json-ld")
    g.parse(join(MODELS_PATH, "agents", "isaac-sim.json"), format="json-ld")

    obj_poses = get_object_poses(g)
    pprint(obj_poses)


if __name__ == "__main__":
    main()
