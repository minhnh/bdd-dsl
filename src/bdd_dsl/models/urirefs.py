from bdd_dsl.models.namespace import (
    NS_TRANS,
    NS_MM_GEOM,
    NS_MM_GEOM_REL,
    NS_MM_GEOM_COORD,
    NS_MM_GEOM_EXT,
    NS_MM_PROB,
    NS_MM_ENV,
)

# Transformation
URI_TRANS_HAS_BODY = NS_TRANS["has-body"]
URI_TRANS_HAS_POSE = NS_TRANS["has-pose"]
URI_TRANS_HAS_POSITION = NS_TRANS["has-position"]
URI_TRANS_HAS_ORIENTATION = NS_TRANS["has-orientation"]
URI_TRANS_OF = NS_TRANS["of"]
URI_TRANS_WRT = NS_TRANS["with-respect-to"]
URI_TRANS_SAMPLED_FROM = NS_TRANS["sampled-from"]
URI_TRANS_DIM = NS_TRANS["dimension"]
URI_TRANS_UPPER = NS_TRANS["upper-bound"]
URI_TRANS_LOWER = NS_TRANS["lower-bound"]

# Geometry structural entities
URI_GEOM_POINT = NS_MM_GEOM["Point"]
URI_GEOM_FRAME = NS_MM_GEOM["Frame"]
URI_GEOM_RIGID_BODY = NS_MM_GEOM["RigidBody"]
URI_GEOM_SIMPLICES = NS_MM_GEOM["simplices"]

# Geometry spatial relations
URI_GEOM_POSITION = NS_MM_GEOM_REL["Position"]
URI_GEOM_ORIENTATION = NS_MM_GEOM_REL["Orientation"]
URI_GEOM_POSE = NS_MM_GEOM_REL["Pose"]
URI_GEOM_OF = NS_MM_GEOM_REL["of"]
URI_GEOM_WRT = NS_MM_GEOM_REL["with-respect-to"]

# Geometry coordinates
URI_GEOM_POSE_COORD = NS_MM_GEOM_COORD["PoseCoordinate"]
URI_GEOM_POSITION_COORD = NS_MM_GEOM_COORD["PositionCoordinate"]
URI_GEOM_ORIENTATION_COORD = NS_MM_GEOM_COORD["OrientationCoordinate"]
URI_GEOM_POSE_REF = NS_MM_GEOM_COORD["PoseReference"]
URI_GEOM_POSITION_REF = NS_MM_GEOM_COORD["PositionReference"]
URI_GEOM_ORIENTATION_REF = NS_MM_GEOM_COORD["OrientationReference"]
URI_GEOM_OF_POSE = NS_MM_GEOM_COORD["of-pose"]
URI_GEOM_OF_POSITION = NS_MM_GEOM_COORD["of-position"]
URI_GEOM_OF_ORIENTATION = NS_MM_GEOM_COORD["of-orientation"]

# Geometry extension
URI_GEOM_POSE_FROM_POS_ORN = NS_MM_GEOM_EXT["PoseFromPositionOrientation"]

# Probability
URI_PROB_SAMPLED_QUANTITY = NS_MM_PROB["SampledQuantity"]
URI_PROB_DISCRETE = NS_MM_PROB["Discrete"]
URI_PROB_CONTINUOUS = NS_MM_PROB["Continuous"]
URI_PROB_UNIFORM = NS_MM_PROB["Uniform"]
URI_PROB_UNIFORM_ROTATION = NS_MM_PROB["UniformRotation"]
URI_PROB_DIM = NS_MM_PROB["dimension"]
URI_PROB_LOWER = NS_MM_PROB["lower-bound"]
URI_PROB_UPPER = NS_MM_PROB["upper-bound"]
URI_PROB_FROM_DISTRIBUTION = NS_MM_PROB["from-distribution"]

# Environment
URI_ENV_OBJECT = NS_MM_ENV["Object"]
URI_ENV_HAS_OBJ = NS_MM_ENV["has-object"]
URI_ENV_OF_OBJ = NS_MM_ENV["of-object"]
URI_ENV_RIGID_OBJ = NS_MM_ENV["RigidObject"]
