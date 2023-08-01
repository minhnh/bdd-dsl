# SPDX-License-Identifier:  GPL-3.0-or-later
import abc
from bdd_dsl.events.event_handler import EventHandler
from py_trees.behaviour import Behaviour as PTBehaviour
from py_trees.common import Status as PTStatus


class ActionWithEvents(PTBehaviour, metaclass=abc.ABCMeta):
    def __init__(self, name: str, event_loop: EventHandler, start_event: str, end_event: str):
        super().__init__(name)
        self._event_loop = event_loop
        for e_id in [start_event, end_event]:
            if event_loop.has_event(e_id):
                continue
            raise ValueError(
                f"event '{e_id}' used by action '{name}' not found in event loop '{event_loop.id}'"
            )
        self._start_event = start_event
        self._end_event = end_event

    @property
    def start_event(self):
        return self._start_event

    @property
    def end_event(self):
        return self._end_event

    def initialise(self):
        self._initialise()
        self._event_loop.produce(self._start_event)

    @abc.abstractmethod
    def _initialise(self):
        """
        called before start event get produced
        """
        raise NotImplementedError(f"[{self.name}]: EventBehaviour._initialise() not implemented")

    def terminate(self, new_status: PTStatus):
        self._event_loop.produce(self._end_event)
        self._terminate(new_status)

    @abc.abstractmethod
    def _terminate(self, new_status: PTStatus):
        """
        called after end event get produced
        """
        raise NotImplementedError(f"[{self.name}]: EventBehaviour._terminate() not implemented")
