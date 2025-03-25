from rdflib import Namespace, Graph
from rdf_utils.namespace import NS_MM_GEOM, NS_MM_GEOM_REL, NS_MM_GEOM_COORD, NS_MM_ENV
from bdd_dsl.models.uri import (
    URI_MM_BDD,
    URI_MM_BHV,
    URI_MM_SIM,
    URI_MM_TASK,
)

# Namespaces
NS_MM_BDD = Namespace(URI_MM_BDD)
NS_MM_BHV = Namespace(URI_MM_BHV)
NS_MM_TASK = Namespace(URI_MM_TASK)
NS_MM_SIM = Namespace(URI_MM_SIM)

# Prefixes
PREFIX_GEOM = "geom"
PREFIX_GEOM_REL = "geom-rel"
PREFIX_GEOM_COORD = "geom-coord"
PREFIX_ENV = "mm-env"

PREFIX_TRANS = "trans"

# Namespace manager
__tmp = Graph()
__tmp.bind(PREFIX_GEOM, NS_MM_GEOM)
__tmp.bind(PREFIX_GEOM_REL, NS_MM_GEOM_REL)
__tmp.bind(PREFIX_GEOM_COORD, NS_MM_GEOM_COORD)
__tmp.bind(PREFIX_ENV, NS_MM_ENV)
NS_MANAGER = __tmp.namespace_manager
