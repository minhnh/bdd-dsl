# SPDX-License-Identifier:  GPL-3.0-or-later
import numpy as np
from typing import Any, Optional
from rdflib import Graph, Literal, URIRef, RDF
from rdflib.paths import ZeroOrMore
from rdflib.term import Node
from bdd_dsl.models.urirefs import (
    URI_DISTRIB_DIM,
    URI_DISTRIB_FROM_DISTRIBUTION,
    URI_DISTRIB_LOWER,
    URI_DISTRIB_UNIFORM_ROTATION,
    URI_DISTRIB_UPPER,
    URI_GEOM_EULER_ANGLES,
    URI_GEOM_QUATERNION,
    URI_DISTRIB_UNIFORM,
    URI_DISTRIB_CONTINUOUS,
    URI_GEOM_ROTATION_MATRIX,
)


KEY_TYPE = "type"
KEY_VALUE = "value"
KEY_SAMPLED_QTY = "sampled quantity"
KEY_RESAMPLE = "resample"
KEY_SCALAR_FIRST = "scalar_first"
KEY_SEQ = "seq"
KEY_DEGREES = "degrees"


def load_node_as_literal(node: Optional[Node]) -> Any:
    if not isinstance(node, Literal):
        return None

    return node.toPython()


def load_distribution_data(graph: Graph, distrib_id: URIRef):
    distrib_types = set(graph.objects(subject=distrib_id, predicate=RDF.type))
    assert len(distrib_types) > 0

    if URI_DISTRIB_UNIFORM_ROTATION in distrib_types:
        return distrib_types, {}

    if URI_DISTRIB_UNIFORM in distrib_types:
        distrib_data = {}
        dimension_literal = graph.value(subject=distrib_id, predicate=URI_DISTRIB_DIM)
        dimension = load_node_as_literal(dimension_literal)
        assert (
            dimension is not None
        ), f"distribution '{distrib_id}' has invalid dimension '{dimension_literal}'"

        upper_bound_gen = graph.objects(
            subject=distrib_id, predicate=(URI_DISTRIB_UPPER / (RDF.rest * ZeroOrMore) / RDF.first)
        )
        assert (
            upper_bound_gen is not None
        ), f"Uniform distribution '{distrib_id}' does not have upper-bound property"

        upper_bounds = []
        for bound_literal in upper_bound_gen:
            upper_bound_val = load_node_as_literal(bound_literal)
            assert (
                upper_bound_val is not None
            ), f"distribution '{distrib_id}' has invalid upper bound '{bound_literal}'"
            upper_bounds.append(upper_bound_val)

        lower_bound_gen = list(
            graph.objects(
                subject=distrib_id,
                predicate=(URI_DISTRIB_LOWER / (RDF.rest * ZeroOrMore) / RDF.first),
            )
        )
        assert (
            lower_bound_gen is not None
        ), f"Uniform distribution '{distrib_id}' does not have lower-bound property"

        lower_bounds = []
        for bound_literal in lower_bound_gen:
            lower_bound_val = load_node_as_literal(bound_literal)
            assert (
                lower_bound_val is not None
            ), f"distribution '{distrib_id}' has invalid lower bound '{bound_literal}'"
            lower_bounds.append(lower_bound_val)

        assert (
            dimension == len(upper_bounds) and dimension == len(lower_bounds)
        ), f"distribution '{distrib_id}' has mismatching upper/lower bound dimensions: dim={dimension}, upper={upper_bounds}, lower={lower_bounds}"
        distrib_data[URI_DISTRIB_DIM] = dimension
        distrib_data[URI_DISTRIB_UPPER] = upper_bounds
        distrib_data[URI_DISTRIB_LOWER] = lower_bounds

        return distrib_types, distrib_data

    raise RuntimeError(f"Distribution '{distrib_id}' has unhandled types: {distrib_types}")


class SampledQuantityData(object):
    def __init__(self, graph: Graph, quantity_id: URIRef) -> None:
        self.id = quantity_id
        self.distrib_id = graph.value(subject=quantity_id, predicate=URI_DISTRIB_FROM_DISTRIBUTION)
        assert (
            self.distrib_id is not None
        ), f"SampledQuantity '{quantity_id}' does not map to a Distribution"
        assert isinstance(self.distrib_id, URIRef)

        self.distrib_types, self.distrib_data = load_distribution_data(graph, self.distrib_id)

        self.sampled_value = None

    def sample_quantity(self, **kwargs: Any) -> Any:
        resample = kwargs.get(KEY_RESAMPLE, False)
        if self.sampled_value is not None and resample:
            return self.sampled_value

        if URI_DISTRIB_UNIFORM_ROTATION in self.distrib_types:
            try:
                from scipy.spatial.transform import Rotation
            except ImportError:
                raise RuntimeError("to sample random rotations, 'scipy' must be installed")

            rand_rot = Rotation.random()

            if URI_GEOM_QUATERNION in self.distrib_types:
                scalar_first = kwargs.get(KEY_SCALAR_FIRST, True)  # default to (w, x, y, z)
                self.sampled_value = {
                    KEY_TYPE: URI_GEOM_QUATERNION,
                    KEY_VALUE: rand_rot.as_quat(scalar_first=scalar_first),
                }
                return self.sampled_value

            if URI_GEOM_ROTATION_MATRIX in self.distrib_types:
                self.sampled_value = {
                    KEY_TYPE: URI_GEOM_ROTATION_MATRIX,
                    KEY_VALUE: rand_rot.as_matrix(),
                }
                return self.sampled_value

            if URI_GEOM_EULER_ANGLES in self.distrib_types:
                # sequence of axes of rotation, capital letters for intrinsic
                # see scipy documentation for details
                sequence = kwargs.get(KEY_SEQ, "xyz")
                degrees = kwargs.get(KEY_DEGREES, False)
                self.sampled_value = {
                    KEY_TYPE: URI_GEOM_EULER_ANGLES,
                    KEY_VALUE: rand_rot.as_euler(seq=sequence, degrees=degrees),
                }
                return self.sampled_value

            raise RuntimeError(
                f"Distribution '{self.distrib_id}' does not have an accepted rotation format in types: {self.distrib_types}"
            )

        if URI_DISTRIB_UNIFORM in self.distrib_types:
            if URI_DISTRIB_CONTINUOUS in self.distrib_types:
                assert URI_DISTRIB_LOWER in self.distrib_data
                assert URI_DISTRIB_LOWER in self.distrib_data
                self.sampled_value = np.random.uniform(
                    self.distrib_data[URI_DISTRIB_LOWER], self.distrib_data[URI_DISTRIB_UPPER]
                )
                return self.sampled_value

        raise RuntimeError(
            f"Distribution '{self.distrib_id}' has unhandled types: {self.distrib_types}"
        )
