# SPDX-License-Identifier:  GPL-3.0-or-later
import time
from bdd_dsl.behaviours.actions import ActionWithEvents
from py_trees.common import Status as PTStatus


class Heartbeat(ActionWithEvents):
    def __init__(self, name, event_loop, start_event, end_event, **kwargs):
        super().__init__(name, event_loop, start_event, end_event)
        self.heartbeat_duration = kwargs.get("heartbeat_duration", 1.0)
        self.message = kwargs.get("message", "THUMP!")
        self._heartbeat_time = None

    def _initialise(self):
        self._heartbeat_time = time.time()

    def _terminate(self, new_status) -> None:
        pass

    def update(self) -> PTStatus:
        if time.time() - self._heartbeat_time > self.heartbeat_duration:
            self.logger.info(self.message)
            return PTStatus.SUCCESS
        return PTStatus.RUNNING
