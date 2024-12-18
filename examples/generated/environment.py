# SPDX-License-Identifier:  GPL-3.0-or-later
import time
from json import JSONDecodeError
from behave.model import Step
from behave.runner import Context
from rdflib import ConjunctiveGraph
from rdf_utils.uri import URL_SECORO_M
from rdf_utils.resolver import install_resolver
from bdd_dsl.execution.mockup import before_all_mockup, before_scenario
from behave.runner import Context, sys

MODELS = {
    f"{URL_SECORO_M}/acceptance-criteria/bdd/agents/isaac-sim.agn.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/scenes/isaac-agents.scene.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/environments/secorolab.env.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/environments/secorolab.env.geom.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/environments/avl.env.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/environments/avl.env.geom.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/simulation/secorolab-isaac.sim.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/simulation/secorolab.sim.geom.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/simulation/secorolab.sim.geom.distrib.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/scenes/secorolab-env.scene.json": "json-ld",
    #    f"{URL_SECORO_M}/acceptance-criteria/bdd/templates/pickplace.tmpl.json": "json-ld",
    #    f"{URL_SECORO_M}/acceptance-criteria/bdd/pickplace-secorolab-isaac.var.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/templates/sorting.tmpl.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/sorting-secorolab-isaac.var.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/execution/pickplace-secorolab-isaac.exec.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/execution/pickplace-secorolab-mockup.bhv.exec.json": "json-ld",
}


def before_all(context: Context):
    install_resolver()
    g = ConjunctiveGraph()
    for url, fmt in MODELS.items():
        try:
            g.parse(url, format=fmt)
        except JSONDecodeError as e:
            print(f"error parsing '{url}' into graph (format='{fmt}'):\n{e}")
            sys.exit(1)

    context.model_graph = g
    before_all_mockup(context)


def before_step(context: Context, step: Step):
    step_start = time.process_time()
    context.step_start = step_start


def after_step(context: Context, step: Step):
    step_exec_time = time.process_time() - context.step_start
    print(f"\n***Step '{step.name}': exec_time={step_exec_time:.6f}\n\n")
