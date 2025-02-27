# from os.path import join, dirname
import sys
from timeit import default_timer as timer
from urllib.request import HTTPError
from pprint import pprint
from rdflib import Dataset
import pyshacl
from rdf_utils.uri import URL_SECORO_M
from rdf_utils.resolver import install_resolver
from bdd_dsl.geometry import ObjPoseCoordLoader
from bdd_dsl.models.uri import URL_MM_DISTRIB_SHACL, URL_MM_GEOM_EXTS_SHACL


MODEL_URLS = {
    f"{URL_SECORO_M}/acceptance-criteria/bdd/environments/secorolab.env.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/environments/secorolab.env.geom.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/environments/avl.env.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/environments/avl.env.geom.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/simulation/secorolab.sim.geom.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/simulation/secorolab.sim.geom.distrib.json": "json-ld",
}

SHACL_URLS = {
    URL_MM_GEOM_EXTS_SHACL: "turtle",
    URL_MM_DISTRIB_SHACL: "turtle",
}


def main():
    install_resolver()
    g = Dataset()
    for url, fmt in MODEL_URLS.items():
        try:
            g.parse(url, format=fmt)
        except HTTPError as e:
            print(f"unable to open URL (code={e.code}): {e.url}")
            sys.exit(1)
        except Exception as e:
            print(f"unhandled exception ({type(e).__name__}) for URL '{url}':\n{e}")
            sys.exit(2)

    shacl_graph = Dataset()
    for mm_url, fmt in SHACL_URLS.items():
        shacl_graph.parse(mm_url, format=fmt)
    conforms, _, report_text = pyshacl.validate(
        g,
        shacl_graph=shacl_graph,
        data_graph_format="json-ld",
        shacl_graph_format="ttl",
        inference="rdfs",
    )
    assert conforms, f"SHACL not valid:\n{report_text}"

    start = timer()
    obj_pose_loader = ObjPoseCoordLoader(g)
    end = timer()
    print(f"graph querying time: {end - start:.5f}")

    for obj_id in obj_pose_loader.get_object_ids():
        try:
            obj_pose_data = obj_pose_loader.get_obj_pose_coord(graph=g, obj_id=obj_id)
        except Exception as e:
            print(f"skipping '{obj_id}':\n{e}")
            continue

        print(
            f"pose of '{obj_pose_data.id}' (of={obj_pose_data.target_frame}, wrt={obj_pose_data.origin_frame})"
        )

        start = timer()
        obj_poses = obj_pose_data.get_coord_values(resample=True)
        end = timer()
        print(f"pose coordinate values loading time: {end - start:.5f}")
        pprint(obj_poses)


if __name__ == "__main__":
    main()
