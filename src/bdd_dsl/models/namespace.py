from rdflib import Namespace, Graph
from bdd_dsl.models.uri import (
    URI_MM_GEOM,
    URI_MM_GEOM_REL,
    URI_MM_GEOM_COORD,
    URI_MM_GEOM_EXT,
    URI_MM_PROB,
    URI_MM_ENV,
    URI_M_SIM,
    URI_TRANS,
)

# Namespaces
NS_MM_GEOM = Namespace(URI_MM_GEOM)
NS_MM_GEOM_REL = Namespace(URI_MM_GEOM_REL)
NS_MM_GEOM_COORD = Namespace(URI_MM_GEOM_COORD)
NS_MM_GEOM_EXT = Namespace(URI_MM_GEOM_EXT)
NS_MM_PROB = Namespace(URI_MM_PROB)
NS_MM_ENV = Namespace(URI_MM_ENV)

NS_M_SIM = Namespace(URI_M_SIM)

NS_TRANS = Namespace(URI_TRANS)

# Prefixes
PREFIX_GEOM = "geom"
PREFIX_GEOM_REL = "geom-rel"
PREFIX_GEOM_COORD = "geom-coord"
PREFIX_GEOM_EXT = "geom-ext"
PREFIX_PROB = "prob"
PREFIX_ENV = "env"

PREFIX_TRANS = "trans"

# Namespace manager
__tmp = Graph()
__tmp.bind(PREFIX_GEOM, NS_MM_GEOM)
__tmp.bind(PREFIX_GEOM_REL, NS_MM_GEOM_REL)
__tmp.bind(PREFIX_GEOM_COORD, NS_MM_GEOM_COORD)
__tmp.bind(PREFIX_GEOM_EXT, NS_MM_GEOM_EXT)
__tmp.bind(PREFIX_PROB, NS_MM_PROB)
__tmp.bind(PREFIX_ENV, NS_MM_ENV)
__tmp.bind(PREFIX_TRANS, NS_TRANS)
NS_MANAGER = __tmp.namespace_manager
