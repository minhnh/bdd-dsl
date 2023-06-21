from enum import StrEnum, IntEnum
import logging
import time
from typing import List
import zmq
from bdd_dsl.events.event_handler import EventHandler


class MessageKey(StrEnum):
    TYPE = "TYPE"
    DATA = "DATA"
    STATUS = "STATUS"


class ResponseType(IntEnum):
    OK = 0
    INVALID_REQUEST = 1
    UNRECOGNIZED_EVENT = 2
    NOT_TRIGGERED = 3


class RequestType(IntEnum):
    PRODUCE = 0
    CONSUME = 1


class EventDataKey(StrEnum):
    ID = "ID"
    TIMESTAMP = "TIMESTAMP"
    SOURCE = "SOURCE"


class ZmqEventServer(object):
    def __init__(
        self,
        id: str,
        events: List[str],
        hostname: str = "*",
        port: int = 5555,
        queue_size: int = 10,
    ):
        self._queue_size = queue_size
        assert self._queue_size > 0

        # setup event queues
        self._event_queues = {}
        for e_name in events:
            self._event_queues[e_name] = []

        # setup connection
        self.hostname = hostname
        self.port = port
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REP)
        self._socket.bind(f"tcp://{self.hostname}:{self.port}")

    def _handle_e_produce(self, event_data: dict):
        e_id = event_data[EventDataKey.ID]
        while len(self._event_queues[e_id]) >= self._queue_size:
            self._event_queues[e_id].pop(0)
        self._event_queues[e_id].append(event_data)

    def _handle_e_consume(self, event_id: str) -> dict:
        if len(self._event_queues[event_id]) == 0:
            return None
        return self._event_queues[event_id][-1]

    def handle_request(self) -> dict:
        message = self._socket.recv_json()
        response = {MessageKey.STATUS: ResponseType.OK}

        if (
            MessageKey.TYPE not in message
            or MessageKey.DATA not in message
            or EventDataKey.ID not in message[MessageKey.DATA]
        ):
            logging.error(f"request missing required fields: {message}")
            response[MessageKey.STATUS] = ResponseType.INVALID_REQUEST
            self._socket.send_json(response)
            return message

        event_data = message[MessageKey.DATA]
        event_id = event_data[EventDataKey.ID]
        if event_id not in self._event_queues:
            response[MessageKey.STATUS] = ResponseType.UNRECOGNIZED_EVENT
            self._socket.send_json(response)
            return message

        req_type = message[MessageKey.TYPE]
        if req_type == RequestType.PRODUCE:
            # check for required event data fields
            if EventDataKey.TIMESTAMP not in event_data:
                response[MessageKey.STATUS] = ResponseType.INVALID_REQUEST
                self._socket.send_json(response)
                return message

            self._handle_e_produce(event_data)

        elif req_type == RequestType.CONSUME:
            last_event_data = self._handle_e_consume(event_id)
            if last_event_data is None:
                response[MessageKey.STATUS] = ResponseType.NOT_TRIGGERED
            else:
                response[MessageKey.DATA] = last_event_data

        else:
            # unrecognized request type
            logging.error(f"invalid request type: {req_type}")
            response[MessageKey.STATUS] = ResponseType.INVALID_REQUEST

        # send response
        self._socket.send_json(response)
        return message


class ZmqEventClient(EventHandler):
    def __init__(self, id: str, events: List[str], hostname="localhost", port=5555):
        super().__init__(id, events)
        self.hostname = hostname
        self.port = port
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REQ)
        self._socket.connect(f"tcp://{self.hostname}:{self.port}")

    def _send_request(self, req: dict) -> dict:
        self._socket.send_json(req)
        resp = self._socket.recv_json()
        if resp[MessageKey.STATUS] == ResponseType.INVALID_REQUEST:
            raise ValueError(f"has_event: invalid request: {req}")
        return resp

    def has_event(self, event_id: str) -> bool:
        resp = self._send_request(
            {MessageKey.TYPE: RequestType.CONSUME, MessageKey.DATA: {EventDataKey.ID: event_id}}
        )
        if resp[MessageKey.STATUS] == ResponseType.UNRECOGNIZED_EVENT:
            return False
        return True

    def produce(self, event_id: str) -> None:
        self._send_request(
            {
                MessageKey.TYPE: RequestType.PRODUCE,
                MessageKey.DATA: {EventDataKey.ID: event_id, EventDataKey.TIMESTAMP: time.time()},
            }
        )

    def consume(self, event_id):
        """return data for last event with ID, or None if no event has been triggered"""
        resp = self._send_request(
            {MessageKey.TYPE: RequestType.CONSUME, MessageKey.DATA: {EventDataKey.ID: event_id}}
        )
        if resp[MessageKey.STATUS] == ResponseType.UNRECOGNIZED_EVENT:
            raise ValueError(f"consume: unrecognized event: {event_id}")
        return resp
