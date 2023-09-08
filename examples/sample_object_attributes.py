from os.path import join, dirname
from bdd_dsl.utils.json import load_metamodels, query_graph
from bdd_dsl.models.queries import OBJ_POSE_COORD_QUERY
from bdd_dsl.models.frames import OBJ_POSE_FRAME
from pprint import pprint
from pyld import jsonld


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

    # pprint(list(g))
    transformed_model = query_graph(g, OBJ_POSE_COORD_QUERY)
    # pprint(transformed_model)
    framed_model = jsonld.frame(transformed_model, OBJ_POSE_FRAME)
    pprint(framed_model)


if __name__ == "__main__":
    main()
