from rdflib import Namespace, Graph
from rdf_utils.namespace import NS_MM_GEOM, NS_MM_GEOM_REL, NS_MM_GEOM_COORD, NS_MM_ENV
from bdd_dsl.models.uri import (
    URI_MM_BDD,
    URI_MM_BHV,
    URI_MM_SIM,
    URI_MM_TASK,
    URI_MM_GEOM_EXT,
    URI_MM_PROB,
    URI_MM_DISTRIB,
    URI_M_SIM,
    URI_TRANS,
)

# Namespaces
NS_MM_GEOM_EXT = Namespace(URI_MM_GEOM_EXT)
NS_MM_PROB = Namespace(URI_MM_PROB)
NS_MM_DISTRIB = Namespace(URI_MM_DISTRIB)
NS_MM_BDD = Namespace(URI_MM_BDD)
NS_MM_BHV = Namespace(URI_MM_BHV)
NS_MM_TASK = Namespace(URI_MM_TASK)
NS_MM_SIM = Namespace(URI_MM_SIM)

NS_M_SIM = Namespace(URI_M_SIM)

NS_TRANS = Namespace(URI_TRANS)

# Prefixes
PREFIX_GEOM = "geom"
PREFIX_GEOM_REL = "geom-rel"
PREFIX_GEOM_COORD = "geom-coord"
PREFIX_GEOM_EXT = "geom-ext"
PREFIX_PROB = "prob"
PREFIX_ENV = "mm-env"

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
