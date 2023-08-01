# SPDX-License-Identifier:  GPL-3.0-or-later
from abc import abstractmethod, ABC
from typing import List


class EventHandler(ABC):
    def __init__(self, id: str, events: List[str]) -> None:
        self.id = id
        self._events = events

    @property
    def event_names(self) -> List[str]:
        return self._events

    @abstractmethod
    def has_event(self, event_id: str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def produce(self, event_id: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def consume(self, event_id: str):
        raise NotImplementedError()


class SimpleEventLoop(EventHandler):
    def __init__(self, id: str, events: List[str]) -> None:
        super().__init__(id, events)
        self._current_events = {}
        self._future_events = {}
        for event_id in self._events:
            self.register_event(event_id)

    @property
    def event_data(self):
        return self._current_events

    def has_event(self, event_id: str) -> bool:
        return event_id in self._current_events

    def register_event(self, event_id: str):
        if self.has_event(event_id):
            raise ValueError(f"Event loop '{self.id}': duplicate event '{event_id}'")
        self._current_events[event_id] = False
        self._future_events[event_id] = False

    def produce(self, event_id: str) -> None:
        if not self.has_event(event_id):
            raise ValueError(
                f"Event loop '{self.id}': 'produce' request unrecognized event: {event_id}"
            )
        self._future_events[event_id] = True

    def consume(self, event_id: str):
        if not self.has_event(event_id):
            raise ValueError(
                f"Event loop '{self.id}': 'consume' request unrecognized event: {event_id}"
            )
        return self._current_events[event_id]

    def reconfigure(self):
        for event_id in self._future_events:
            self._current_events[event_id] = self._future_events[event_id]
            self._future_events[event_id] = False
