# SPDX-License-Identifier:  GPL-3.0-or-later
from abc import abstractmethod
from typing import Any
from urllib.request import HTTPError
from rdflib import Graph, URIRef, RDF
from rdf_utils.uri import URL_SECORO_M
from rdf_utils.caching import read_url_and_cache

from bdd_dsl.distribution import KEY_SAMPLED_QTY, SampledQuantityData
from bdd_dsl.models.urirefs import (
    URI_GEOM_FROM_ORIENTATION,
    URI_GEOM_FROM_POSITION,
    URI_GEOM_OF,
    URI_GEOM_OF_ORIENTATION,
    URI_GEOM_OF_POSE,
    URI_GEOM_OF_POSITION,
    URI_GEOM_POSE_FROM_POS_ORN,
    URI_DISTRIB_SAMPLED_QUANTITY,
    URI_GEOM_WRT,
    URI_TRANS_HAS_POSE,
)


URL_Q_OBJ_POSE_COORD = f"{URL_SECORO_M}/acceptance-criteria/bdd/queries/object-pose-coord.rq"
URL_Q_SAMPLED_POSE_COORD = f"{URL_SECORO_M}/acceptance-criteria/bdd/queries/sampled-quantities.rq"

KEY_POSITION = "position"
KEY_ORIENTATION = "orientation"


class GeomRelCoordData(object):
    def __init__(self, graph: Graph, rel_id: URIRef, rel_coord_path: URIRef) -> None:
        """
        :param rel_id: URI of the geometric relation
        :param coord_id: URI of the coordinate for the geometric relation
        :param rel_coord_path: path in the RDF graph from the coorinate to the geometric relation
        """
        self.rel_id = rel_id

        self.origin_frame = graph.value(subject=rel_id, predicate=URI_GEOM_WRT)
        assert self.origin_frame is not None and isinstance(self.origin_frame, URIRef)

        self.target_frame = graph.value(subject=rel_id, predicate=URI_GEOM_OF)
        assert self.target_frame is not None and isinstance(self.target_frame, URIRef)

        coord_ids = list(graph.subjects(predicate=rel_coord_path, object=rel_id))
        assert (
            len(coord_ids) == 1
        ), f"Geometric relation '{rel_id}' does not map to exactly 1 coordinate, found {len(coord_ids)}"

        coord_id = coord_ids[0]
        assert isinstance(coord_id, URIRef)

        self.id = coord_id
        self.types = list(graph.objects(subject=coord_id, predicate=RDF.type))

        self.handled_type = None
        self.coord_data = {}

    @abstractmethod
    def get_coord_values(self, **kwargs) -> Any:
        raise NotImplementedError(f"GeomRelCoordData: abstract method callded for '{self.id}'")


class OrientationCoordData(GeomRelCoordData):
    def __init__(self, graph: Graph, orn_id: URIRef) -> None:
        super().__init__(graph=graph, rel_id=orn_id, rel_coord_path=URI_GEOM_OF_ORIENTATION)

        for c_type in self.types:
            if c_type == URI_DISTRIB_SAMPLED_QUANTITY:
                self.handled_type = c_type
                self.coord_data[KEY_SAMPLED_QTY] = SampledQuantityData(
                    graph=graph, quantity_id=self.id
                )

        # if none of the types returns, raise an exception
        assert (
            self.handled_type is not None
        ), f"PositionCoordinate '{self.id}' has unexpected types: {self.types}"

    def get_coord_values(self, **kwargs) -> dict:
        if self.handled_type == URI_DISTRIB_SAMPLED_QUANTITY:
            return self.coord_data[KEY_SAMPLED_QTY].sample_quantity(**kwargs)

        raise RuntimeError(
            f"OrientationCoordinate '{self.id}' has unhandled type: {self.handled_type}"
        )


class PositionCoordData(GeomRelCoordData):
    def __init__(self, graph: Graph, position_id: URIRef) -> None:
        super().__init__(graph=graph, rel_id=position_id, rel_coord_path=URI_GEOM_OF_POSITION)

        for c_type in self.types:
            if c_type == URI_DISTRIB_SAMPLED_QUANTITY:
                self.handled_type = c_type
                self.coord_data[KEY_SAMPLED_QTY] = SampledQuantityData(
                    graph=graph, quantity_id=self.id
                )

        # if none of the types returns, raise an exception
        assert (
            self.handled_type is not None
        ), f"PositionCoordinate '{self.id}' has unexpected types: {self.types}"

    def get_coord_values(self, **kwargs) -> Any:
        if self.handled_type == URI_DISTRIB_SAMPLED_QUANTITY:
            return self.coord_data[KEY_SAMPLED_QTY].sample_quantity(**kwargs)

        raise RuntimeError(
            f"PositionCoordinate '{self.id}' has unhandled type: {self.handled_type}"
        )


class PoseCoordData(GeomRelCoordData):
    def __init__(self, graph: Graph, obj_pose_coord_graph: Graph, pose_id: URIRef) -> None:
        super().__init__(
            graph=obj_pose_coord_graph, rel_id=pose_id, rel_coord_path=URI_GEOM_OF_POSE
        )

        for coord_type in self.types:
            if coord_type == URI_GEOM_POSE_FROM_POS_ORN:
                self.handled_type = coord_type

                position_id = graph.value(self.id, URI_GEOM_FROM_POSITION)
                assert position_id is not None, f"pose '{self.id}' does not map to a Position"
                assert isinstance(position_id, URIRef)
                self.coord_data[KEY_POSITION] = PositionCoordData(graph, position_id)

                orn_id = graph.value(self.id, URI_GEOM_FROM_ORIENTATION)
                assert (
                    orn_id is not None
                ), f"pose '{self.id}' does not map to aOrientationCoordinate"
                assert isinstance(orn_id, URIRef)
                self.coord_data[KEY_ORIENTATION] = OrientationCoordData(graph, orn_id)

        # If none of the types return a dictionary of coordinate data, raise an exception
        assert (
            self.handled_type is not None
        ), f"PoseCoordinate '{self.id}' has unexpected types: {self.types}"

    def get_coord_values(self, **kwargs) -> dict:
        if self.handled_type == URI_GEOM_POSE_FROM_POS_ORN:
            return {
                KEY_POSITION: self.coord_data[KEY_POSITION].get_coord_values(**kwargs),
                KEY_ORIENTATION: self.coord_data[KEY_ORIENTATION].get_coord_values(**kwargs),
            }

        raise RuntimeError(f"PoseCoordinate '{self.id}' has unhandled type: {self.handled_type}")


class ObjPoseCoordLoader(object):
    def __init__(self, graph: Graph) -> None:
        try:
            g_query_str = read_url_and_cache(URL_Q_OBJ_POSE_COORD)
        except HTTPError as e:
            raise RuntimeError(f"unable to open URL (code={e.code}): {URL_Q_OBJ_POSE_COORD}")

        q_result = graph.query(g_query_str)
        assert q_result.type == "CONSTRUCT"
        assert q_result.graph is not None

        self._obj_pose_coord_g = q_result.graph
        self._obj_pose_id_cache = {}
        self._obj_pose_coord_data_cache = {}

    def _get_obj_pose_coord_g(self) -> Graph:
        return self._obj_pose_coord_g

    obj_pose_coord_graph = property(fget=_get_obj_pose_coord_g, doc="read only graph query result")

    def _get_cached_obj_pose_coord_id(self, obj_id: URIRef) -> URIRef:
        if obj_id in self._obj_pose_id_cache:
            pose_id = self._obj_pose_id_cache[obj_id]
        else:
            poses = list(
                self._obj_pose_coord_g.objects(subject=obj_id, predicate=URI_TRANS_HAS_POSE)
            )
            assert (
                len(poses) == 1
            ), f"object '{obj_id}' does not map to exactly 1 pose, found {len(poses)}"

            pose_id = poses[0]
            assert isinstance(pose_id, URIRef)

            self._obj_pose_id_cache[obj_id] = pose_id

        return pose_id

    def get_obj_pose_coord(self, graph: Graph, obj_id: URIRef) -> PoseCoordData:
        pose_id = self._get_cached_obj_pose_coord_id(obj_id)
        if pose_id in self._obj_pose_coord_data_cache:
            return self._obj_pose_coord_data_cache[pose_id]

        pose_coord_data = PoseCoordData(graph, self._obj_pose_coord_g, pose_id)
        self._obj_pose_coord_data_cache[pose_id] = pose_coord_data
        return pose_coord_data
