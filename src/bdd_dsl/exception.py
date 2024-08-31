# SPDX-License-Identifier:  GPL-3.0-or-later
from rdf_utils.constraints import ConstraintViolation


class BDDConstraintViolation(ConstraintViolation):
    def __init__(self, message):
        super().__init__("BDD", message)


class GracefulExit(Exception):
    def __init__(self, signum: int):
        self.signum = signum
