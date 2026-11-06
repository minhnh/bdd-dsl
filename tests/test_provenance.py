# SPDX-License-Identifier: Apache-2.0
import io
import json
from types import MappingProxyType
from uuid import UUID, uuid4

import pytest
from rdflib import URIRef

from bdd_dsl.provenance import ProvenanceJournal, read_journal

POLICY = URIRef("urn:policy")
OBSERVATION = URIRef("urn:observation")
START_EVENT = URIRef("urn:scenario-start")
END_EVENT = URIRef("urn:scenario-end")


@pytest.fixture
def journal(tmp_path):
    with ProvenanceJournal(
        tmp_path / "evidence.jsonl",
        uuid4(),
        use_sim_time=True,
    ) as writer:
        yield writer, tmp_path / "evidence.jsonl"


def details(sample_id=0):
    return {
        "sample_ids": [sample_id],
        "measurement": {"distance": 0.5},
    }


def test_records_share_one_trs_and_preserve_order_and_sample_references(journal):
    writer, path = journal
    evidence = details()
    writer.record_observation(0, OBSERVATION, 1.0)
    for policy, stamp, result in (
        (URIRef("urn:first"), 2.0, True),
        (URIRef("urn:second"), 1.0, False),
    ):
        writer.record_evaluation(policy, stamp, result, MappingProxyType(evidence))
    evidence["measurement"]["distance"] = 99
    records = list(read_journal(path))  # Complete records are readable before close.
    header, sample, first, second = records
    assert "stamp" not in header
    record_ids = [record["record_id"] for record in records]
    assert all(isinstance(record_id, UUID) for record_id in record_ids)
    assert len(set(record_ids)) == len(records)
    assert all("sequence" not in record for record in records)
    assert {record["scenario_context_id"] for record in records} == {writer.context_id}
    assert isinstance(writer.trs_id, URIRef)
    assert isinstance(header["model_uri"], URIRef)
    assert isinstance(header["data"]["trs_id"], URIRef)
    assert header["data"] == {"use_sim_time": True, "trs_id": writer.trs_id}
    assert sample["model_uri"] == OBSERVATION
    assert all(
        "kind" not in record and "clock_id" not in record and "trs_id" not in record
        for record in records
    )
    assert first["model_uri"] == URIRef("urn:first")
    assert second["model_uri"] == URIRef("urn:second")
    assert first["stamp"] > second["stamp"]  # Clock readings do not define record order.
    assert (
        first["data"]["details"]["sample_ids"]
        == second["data"]["details"]["sample_ids"]
        == [sample["data"]["sample_id"]]
    )
    assert (
        first["data"]["details"]["measurement"]
        == second["data"]["details"]["measurement"]
        != evidence["measurement"]
    )


def test_repeated_and_out_of_order_readings_keep_distinct_sample_ids(journal):
    writer, path = journal
    for sample_id, stamp in enumerate((2.0, 2.0, 0.0)):
        writer.record_observation(sample_id, OBSERVATION, stamp)
        writer.record_evaluation(POLICY, stamp, True, details(sample_id))
    samples = [r for r in read_journal(path) if r["model_uri"] == OBSERVATION]
    assert len({s["data"]["sample_id"] for s in samples}) == len(samples) == 3
    assert [s["stamp"] for s in samples] == [2.0, 2.0, 0.0]


@pytest.mark.parametrize("result", [True, False, "unknown", None])
def test_empty_evaluations_preserve_all_result_states(journal, result):
    writer, path = journal
    writer.record_evaluation(POLICY, 0.0, result, {})
    evaluation = list(read_journal(path))[-1]
    assert type(evaluation["data"]["result"]) is type(result)
    assert evaluation["data"]["result"] == result
    assert evaluation["data"]["details"] == {}


@pytest.mark.parametrize("bad_value", [object(), float("nan")])
def test_invalid_details_raise_without_writing_or_failing_the_journal(journal, bad_value):
    writer, path = journal
    evidence = {**details(), "bad": bad_value}
    writer.record_observation(0, OBSERVATION, 1.0)
    before = path.read_bytes()
    with pytest.raises((TypeError, ValueError)):
        writer.record_evaluation(POLICY, 1.0, False, evidence)
    assert path.read_bytes() == before
    assert not writer.failed
    writer.create_record(END_EVENT, 2.0)


@pytest.mark.parametrize(
    ("sample_id", "observation_uri", "stamp"),
    [
        (-1, OBSERVATION, 1.0),
        (True, OBSERVATION, 1.0),
        (0, URIRef(""), 1.0),
        (0, OBSERVATION, float("nan")),
    ],
)
def test_invalid_observation_metadata_does_not_write_records(
    journal, sample_id, observation_uri, stamp
):
    writer, path = journal
    before = path.read_bytes()
    with pytest.raises(ValueError):
        writer.record_observation(sample_id, observation_uri, stamp)
    assert path.read_bytes() == before


def test_evaluation_rejects_unknown_or_invalid_references_before_writing(journal):
    writer, path = journal
    writer.record_observation(1, OBSERVATION, 1.0)
    before = path.read_bytes()
    for references in ([99], [True], "not-a-list"):
        with pytest.raises(ValueError):
            writer.record_evaluation(POLICY, 1.0, None, {"sample_ids": references})
        assert path.read_bytes() == before


def test_sample_is_written_once_and_its_identity_cannot_be_reassigned(journal):
    writer, path = journal
    record_id = writer.record_observation(0, OBSERVATION, 1.0)
    assert list(read_journal(path))[-1]["record_id"] == record_id
    before = path.read_bytes()
    assert writer.record_observation(0, OBSERVATION, 1.0) is None
    with pytest.raises(ValueError):
        writer.record_observation(0, OBSERVATION, 2.0)
    assert path.read_bytes() == before


def test_lifecycle_records_reference_model_events_without_a_kind(journal):
    writer, path = journal
    data = {"record_id": "user data", "scenario_context_id": "user data"}
    writer.create_record(START_EVENT, 1.0, data)
    writer.create_record(END_EVENT, 1.0)
    start, end = list(read_journal(path))[1:]
    assert start["model_uri"] == START_EVENT
    assert end["model_uri"] == END_EVENT
    assert start["stamp"] == end["stamp"]
    assert start["record_id"] != end["record_id"]
    assert isinstance(start["record_id"], UUID)
    assert start["scenario_context_id"] == writer.context_id
    assert "data" not in end
    assert start["data"] == data
    assert "kind" not in start and "kind" not in end


def test_new_journals_do_not_overwrite_or_share_contexts(tmp_path):
    paths = [tmp_path / name for name in ("first.jsonl", "second.jsonl")]
    contexts = [uuid4(), uuid4()]
    for path, context, simulated in zip(paths, contexts, (True, False)):
        with ProvenanceJournal(path, context, use_sim_time=simulated) as writer:
            writer.create_record(START_EVENT, 0.0)
        assert {r["scenario_context_id"] for r in read_journal(path)} == {str(context)}
        clock = next(read_journal(path))["data"]
        assert clock["use_sim_time"] is simulated
        assert clock["trs_id"] == (URIRef(f"urn:uuid:{context}#clock") if simulated else None)
    before = paths[0].read_bytes()
    with pytest.raises(FileExistsError):
        ProvenanceJournal(paths[0], uuid4(), use_sim_time=True)
    assert paths[0].read_bytes() == before


def test_recovery_validates_clock_metadata(tmp_path):
    path = tmp_path / "evidence.jsonl"
    with ProvenanceJournal(path, uuid4(), use_sim_time=True):
        pass
    header = next(read_journal(path))
    for data in (
        {},
        {"use_sim_time": True, "trs_id": None},
        {"use_sim_time": True, "trs_id": ""},
        {"use_sim_time": True, "trs_id": []},
        {"use_sim_time": True, "trs_id": {}},
        {"use_sim_time": False, "trs_id": "urn:test:clock"},
        {"use_sim_time": "true", "trs_id": "urn:test:clock"},
    ):
        path.write_text(json.dumps({**header, "data": data}, default=str) + "\n")
        with pytest.raises(ValueError):
            list(read_journal(path))


def test_create_record_always_appends_with_a_fresh_uuid(journal):
    writer, path = journal
    before = path.read_bytes()
    with pytest.raises(TypeError):
        writer.create_record(START_EVENT, 0.0, {"bad": object()})
    assert path.read_bytes() == before
    first = writer.create_record(START_EVENT, 0.0)
    second = writer.create_record(START_EVENT, 0.0)
    assert isinstance(first, UUID) and isinstance(second, UUID)
    assert first != second
    assert [r["record_id"] for r in read_journal(path)][1:] == [first, second]
    assert path.read_bytes().startswith(before)


def test_invalid_records_are_not_written(journal):
    writer, path = journal
    for stamp in (float("inf"), 10**400, True):
        with pytest.raises(ValueError):
            writer.create_record(START_EVENT, stamp)
    with pytest.raises(ValueError):
        writer.create_record(URIRef(""), 0.0)
    assert len(list(read_journal(path))) == 1
    assert isinstance(writer.create_record(START_EVENT, -1.0), UUID)
    assert len(list(read_journal(path))) == 2


class FailingStream(io.BytesIO):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode

    def write(self, data):
        if self.mode == "short":
            return super().write(data[: len(data) // 2])
        if self.mode == "write":
            raise OSError("disk unavailable")
        return super().write(data)

    def flush(self):
        if self.mode == "flush":
            raise OSError("flush failed")
        return super().flush()

    def close(self):
        if self.mode == "close":
            raise OSError("close failed")
        super().close()


@pytest.mark.parametrize("mode", ["short", "write", "flush"])
def test_io_failure_poisoning_rejects_all_later_writes(journal, mode):
    writer, _ = journal
    writer.record_observation(0, OBSERVATION, 1.0)
    writer._stream.close()
    writer._stream = stream = FailingStream(mode)
    with pytest.raises(OSError):
        writer.record_evaluation(POLICY, 1.0, True, details())
    before = stream.getvalue()
    assert writer.failed
    with pytest.raises(OSError):
        writer.create_record(END_EVENT, 2.0)
    with pytest.raises(OSError):
        writer.record_observation(0, OBSERVATION, 1.0)
    assert stream.getvalue() == before


def test_close_is_idempotent_and_reports_failure(journal):
    writer, _ = journal
    writer._stream.close()
    writer._stream = FailingStream("close")
    with pytest.raises(OSError):
        writer.close()
    assert writer.failed
    writer.close()
    with pytest.raises(OSError):
        writer.create_record(END_EVENT, 1.0)
    writer._stream.mode = "normal"
    writer._stream.close()


@pytest.mark.parametrize("tail", [b'{"partial":', b"\xff", b"{}"])
def test_recovery_ignores_only_unterminated_final_line(journal, tail):
    writer, path = journal
    writer.create_record(END_EVENT, 1.0)
    writer.close()
    complete = list(read_journal(path))
    with path.open("ab") as stream:
        stream.write(tail)
    assert list(read_journal(path)) == complete


@pytest.mark.parametrize("bad_line", [b"not-json\n", b"{}\n", b"[]\n", b'{"bad":NaN}\n'])
def test_recovery_rejects_complete_malformed_interior_records(journal, bad_line):
    writer, path = journal
    writer.close()
    with path.open("ab") as stream:
        stream.write(bad_line + b"{}\n")
    with pytest.raises(ValueError):
        list(read_journal(path))


def test_recovery_rejects_invalid_records(journal):
    writer, path = journal
    writer.create_record(END_EVENT, 1.0)
    writer.close()
    records = list(read_journal(path))
    for field, value in (
        ("record_id", "not-a-uuid"),
        ("record_id", None),
        ("record_id", 42),
        ("record_id", str(records[0]["record_id"])),
        ("scenario_context_id", str(uuid4())),
        ("schema_version", 99),
        ("stamp", float("inf")),
        ("stamp", "not-a-timestamp"),
        ("stamp", []),
        ("model_uri", ""),
        ("model_uri", 42),
        ("model_uri", True),
        ("model_uri", None),
        ("model_uri", []),
        ("model_uri", {}),
        ("data", []),
    ):
        changed = [records[0], {**records[1], field: value}]
        path.write_text("".join(json.dumps(record, default=str) + "\n" for record in changed))
        with pytest.raises(ValueError):
            list(read_journal(path))
