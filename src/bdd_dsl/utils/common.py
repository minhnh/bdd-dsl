# SPDX-License-Identifier:  GPL-3.0-or-later
import signal
from importlib.metadata import version

import numpy as np

from bdd_dsl.exception import GracefulExit


BDD_DSL_VERSION = version("bdd-dsl")


def raise_graceful_exit_handler(signum, frame):
    raise GracefulExit(signum)


def register_termination_signals(handled_signals=[signal.SIGINT, signal.SIGTERM]):
    for signum in handled_signals:
        signal.signal(signum, raise_graceful_exit_handler)


def check_or_convert_ndarray(in_array) -> np.ndarray:
    if isinstance(in_array, np.ndarray):
        return in_array

    if isinstance(in_array, list) or isinstance(in_array, tuple):
        return np.array(in_array)

    raise ValueError(
        f"input of type '{type(in_array)}' is not an instance numpy.ndarray and cannot be converted into one."
    )
