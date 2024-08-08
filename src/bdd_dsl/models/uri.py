# SPDX-License-Identifier:  GPL-3.0-or-later
from rdf_utils.uri import URL_SECORO, URL_SECORO_MM, URL_SECORO_M

URI_MM_GEOM_EXT = f"{URL_SECORO_MM}/geometry#"

URI_MM_DISTRIB = f"{URL_SECORO_MM}/distribution#"

URL_SESAME = "https://hbrs-sesame.github.io"

URI_TRANS = f"{URL_SECORO}/transformations/"

URI_MM_PROB = f"{URL_SESAME}/metamodels/variation/probability#"
URI_MM_TASK = f"{URL_SECORO_MM}/task#"
URI_MM_AGENT = f"{URL_SECORO_MM}/agent#"
URI_MM_BDD = f"{URL_SECORO_MM}/acceptance-criteria/bdd#"
URI_MM_EVENT = f"{URL_SESAME}/metamodels/coordination/event#"
URI_MM_BT = f"{URL_SESAME}/metamodels/coordination/behaviour-tree#"
URI_MM_PY = f"{URL_SESAME}/metamodels/languages/python#"

URI_M_CRDN = f"{URL_SESAME}/models/coordination/"
URI_M_AC = f"{URL_SECORO_M}/acceptance-criteria/"
URI_M_BDD = f"{URL_SECORO_M}/acceptance-criteria/bdd/"
URI_M_ENV = f"{URL_SECORO_M}/environments/"
URI_M_AGENT = f"{URL_SECORO_M}/agents/"
URI_M_SIM = f"{URL_SESAME}/models/simulation/"

# URL to SHACL constraints
URL_MM_GEOM_EXTS_SHACL = f"{URL_SECORO_MM}/acceptance-criteria/bdd/geometry-exts.shacl.ttl"
URL_MM_DISTRIB_SHACL = f"{URL_SECORO_MM}/acceptance-criteria/bdd/distribution.shacl.ttl"
