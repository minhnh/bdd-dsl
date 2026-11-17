# SPDX-License-Identifier: Apache-2.0
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from rdf_utils import DatasetFormat
from rdflib import RDF, BNode, Dataset, Graph, URIRef
from rdflib.namespace import PROV, TIME
from trinary import Unknown

from bdd_dsl.models.observation import ObsDetailKey, ObservationStamped, init_sample_details
from bdd_dsl.prov import RecordingSession, ScenarioExecRecorder, read_journal

POLICY = URIRef("urn:policy")
OBSERVATION = URIRef("urn:observation")
START_EVENT = URIRef("urn:scenario-start")
END_EVENT = URIRef("urn:scenario-end")


AGENT = URIRef("urn:test:agent")


def _journal(path, context_id, use_sim_time):
    session = RecordingSession(Path(path).parent, AGENT, use_sim_time=use_sim_time)
    return ScenarioExecRecorder(path, context_id, session)


@pytest.fixture
def journal(tmp_path):
    with _journal(
        tmp_path / "evidence.jsonl",
        uuid4(),
        use_sim_time=True,
    ) as writer:
        yield writer, tmp_path / "evidence.jsonl"


def details(sample_id=0):
    return {
        ObsDetailKey.SAMPLE_IDS: [sample_id],
        "measurement": {"distance": 0.5},
    }


@pytest.mark.parametrize("use_sim_time", [False, True])
def test_journals_create_execution_bundles_and_distinct_simulation_trs_ids(tmp_path, use_sim_time):
    context_id = uuid4()
    session = RecordingSession(tmp_path, AGENT, use_sim_time=use_sim_time)
    with (
        ScenarioExecRecorder(tmp_path / "first.jsonl", context_id, session) as first,
        ScenarioExecRecorder(tmp_path / "second.jsonl", context_id, session) as second,
    ):
        assert first.bundle_id != second.bundle_id
        for writer in (first, second):
            assert writer.execution_id == URIRef(context_id.urn)
            assert writer.graph.store is writer.dataset.store
            assert writer.graph.identifier == writer.bundle_id
            assert (writer.bundle_id, RDF.type, PROV.Bundle) in writer.graph
            assert (writer.bundle_id, PROV.wasAttributedTo, AGENT) in writer.graph
            assert (writer.execution_id, RDF.type, PROV.Activity) in writer.graph
            assert (writer.execution_id, PROV.used, session.model_id) in writer.graph
            assert (writer.execution_id, PROV.wasAssociatedWith, AGENT) in writer.graph
            assert (
                writer.bundle_id,
                PROV.wasGeneratedBy,
                writer.execution_id,
            ) in writer.dataset.default_graph
            systems = set(writer.graph.subjects(RDF.type, TIME.TRS))
            assert systems == ({writer.trs_id} if use_sim_time else set())
            for trs_id in systems:
                assert (trs_id, RDF.type, PROV.Entity) in writer.graph
                assert (writer.execution_id, PROV.used, trs_id) in writer.graph
        if use_sim_time:
            assert isinstance(first.trs_id, URIRef)
            assert UUID(str(first.trs_id).removeprefix("urn:uuid:"))
            assert first.trs_id != second.trs_id
        else:
            assert first.trs_id is None and second.trs_id is None


def test_records_share_one_trs_and_preserve_order_and_sample_references(journal):
    writer, path = journal
    evidence = details()
    writer.record_observation(0, OBSERVATION, 1.0)
    for policy, stamp, result in (
        (URIRef("urn:first"), 2.0, True),
        (URIRef("urn:second"), 1.0, False),
    ):
        writer.record_evaluation(policy, stamp, result, evidence)
    evidence["measurement"]["distance"] = 99
    records = list(read_journal(path))  # Complete records are readable before close.
    sample, first, second = records
    record_ids = [record["record_id"] for record in records]
    assert all(isinstance(record_id, UUID) for record_id in record_ids)
    assert len(set(record_ids)) == len(records)
    assert all(
        "sequence" not in record and "scenario_context_id" not in record for record in records
    )
    assert {record["execution_id"] for record in records} == {writer.execution_id}
    assert sample["model_uri"] == OBSERVATION
    assert all(
        "kind" not in record and "clock_id" not in record and "trs_id" not in record
        for record in records
    )
    assert first["model_uri"] == URIRef("urn:first")
    assert second["model_uri"] == URIRef("urn:second")
    assert first["stamp"] > second["stamp"]  # Clock readings do not define record order.
    assert (
        first["data"]["details"][ObsDetailKey.SAMPLE_IDS]
        == second["data"]["details"][ObsDetailKey.SAMPLE_IDS]
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
            writer.record_evaluation(POLICY, 1.0, None, {ObsDetailKey.SAMPLE_IDS: references})
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
    data = {"record_id": "user data", "execution_id": "user data"}
    writer.create_record(START_EVENT, 1.0, data)
    writer.create_record(END_EVENT, 1.0)
    start, end = list(read_journal(path))
    assert start["model_uri"] == START_EVENT
    assert end["model_uri"] == END_EVENT
    assert start["stamp"] == end["stamp"]
    assert start["record_id"] != end["record_id"]
    assert isinstance(start["record_id"], UUID)
    assert start["execution_id"] == writer.execution_id
    assert "data" not in end
    assert start["data"] == data
    assert "kind" not in start and "kind" not in end


def test_new_journals_do_not_overwrite_or_share_contexts(tmp_path):
    paths = [tmp_path / name for name in ("first.jsonl", "second.jsonl")]
    contexts = [uuid4(), uuid4()]
    for path, context, simulated in zip(paths, contexts, (True, False)):
        with _journal(path, context, use_sim_time=simulated) as writer:
            writer.create_record(START_EVENT, 0.0)
        assert {r["execution_id"] for r in read_journal(path)} == {URIRef(context.urn)}
    before = paths[0].read_bytes()
    dataset = writer.dataset
    before_quads = set(dataset.quads())
    with pytest.raises(FileExistsError):
        ScenarioExecRecorder(paths[0], uuid4(), writer.session)
    assert paths[0].read_bytes() == before
    assert set(dataset.quads()) == before_quads


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
    assert [r["record_id"] for r in read_journal(path)] == [first, second]
    assert path.read_bytes().startswith(before)


def test_invalid_records_are_not_written(journal):
    writer, path = journal
    for stamp in (float("inf"), 10**400, True):
        with pytest.raises(ValueError):
            writer.create_record(START_EVENT, stamp)
    with pytest.raises(ValueError):
        writer.create_record(URIRef(""), 0.0)
    assert len(list(read_journal(path))) == 0
    assert isinstance(writer.create_record(START_EVENT, -1.0), UUID)
    assert len(list(read_journal(path))) == 1


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
    writer.create_record(START_EVENT, 0.0)
    writer.create_record(END_EVENT, 1.0)
    writer.close()
    records = list(read_journal(path))
    for field, value in (
        ("record_id", "not-a-uuid"),
        ("record_id", None),
        ("record_id", 42),
        ("record_id", str(records[0]["record_id"])),
        ("execution_id", uuid4().urn),
        ("execution_id", ""),
        ("execution_id", None),
        ("execution_id", 42),
        ("execution_id", True),
        ("execution_id", []),
        ("execution_id", {}),
        ("schema_version", 99),
        ("stamp", float("inf")),
        ("stamp", "not-a-timestamp"),
        ("stamp", []),
        ("stamp", None),
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


def _policy(evaluated=True):
    return SimpleNamespace(
        id=URIRef(uuid4().urn),
        evaluator_id=URIRef(uuid4().urn) if evaluated else None,
        evaluator=SimpleNamespace(get_config=Mock(return_value={})) if evaluated else None,
    )


def test_configuration_tracks_policy_and_evaluator_and_skips_direct_policies(journal):
    writer, _ = journal
    policy, direct = _policy(), _policy(evaluated=False)
    config = {"limit": 1.0}
    policy.evaluator.get_config.return_value = config
    configuration = writer.record_policy_config(policy)
    assert isinstance(writer.policy_configs[policy.id], URIRef)
    assert writer.policy_configs[policy.id] == configuration
    assert (configuration, PROV.wasDerivedFrom, policy.id) in writer.graph
    assert (configuration, PROV.wasDerivedFrom, policy.evaluator_id) in writer.graph
    assert json.loads(str(writer.graph.value(configuration, PROV.value))) == config
    before = set(writer.graph)
    assert writer.record_policy_config(direct) is None
    assert set(writer.graph) == before
    assert direct.id not in writer.policy_configs


@pytest.mark.parametrize("missing", ["evaluator", "evaluator_id"])
def test_inconsistent_evaluator_configuration_raises(journal, missing):
    writer, _ = journal
    policy = _policy()
    setattr(policy, missing, None)
    before = set(writer.graph)
    with pytest.raises(ValueError, match=missing) as error:
        writer.record_policy_config(policy)
    assert str(policy.id) in str(error.value)
    assert set(writer.graph) == before
    assert not writer.policy_configs


def test_metadata_is_a_snapshot_in_the_execution_bundle(journal):
    writer, path = journal
    model_uri = URIRef(uuid4().urn)
    data = {"nested": {"items": ["first"]}}
    entity = writer.record_metadata(model_uri, data)
    assert (entity, RDF.type, PROV.Entity) in writer.graph
    assert (writer.execution_id, PROV.used, entity) in writer.graph
    assert (entity, PROV.wasDerivedFrom, model_uri) in writer.graph
    value = writer.graph.value(entity, PROV.value)
    assert value.datatype == RDF.JSON
    assert json.loads(str(value)) == data
    data["nested"]["items"].append("later")
    assert json.loads(str(value)) != data
    assert not list(read_journal(path))


@pytest.mark.parametrize("invalid, error", [(object(), TypeError), (float("nan"), ValueError)])
def test_invalid_metadata_does_not_modify_the_bundle(journal, invalid, error):
    writer, _ = journal
    before = set(writer.graph)
    with pytest.raises(error):
        writer.record_metadata(POLICY, {"invalid": invalid})
    assert set(writer.graph) == before


@pytest.mark.parametrize("error", ["metadata", "serialization", "write"])
def test_callback_errors_propagate(journal, error):
    recorder, _ = journal
    details = {ObsDetailKey.SAMPLE_IDS: [1]} if error == "metadata" else {"bad": object()}
    if error == "write":
        recorder.record_evaluation = Mock(side_effect=OSError("disk full"))
        details = {}
    expected = {"metadata": ValueError, "serialization": TypeError, "write": OSError}
    with pytest.raises(expected[error]):
        recorder.record_policy_eval(_policy(), 0.0, True, details)


@pytest.mark.parametrize(
    "result, expected",
    [(True, True), (False, False), (Unknown, "unknown"), (None, None)],
)
def test_callback_preserves_journal_result_representation(journal, result, expected):
    recorder, path = journal
    recorder.record_policy_eval(_policy(evaluated=False), 0.0, result, {})
    (record,) = read_journal(path)
    recorded = record["data"]["result"]
    assert type(recorded) is type(expected)
    assert recorded == expected


def _session(output_dir, model=None, *, dataset_format=DatasetFormat.TRIG):
    session = RecordingSession(output_dir, AGENT, dataset_format=dataset_format, use_sim_time=False)
    if model is not None:
        session.model_graph.__iadd__(model)
    return session


def _open_recorder(session):
    context_id = uuid4()
    recorder = ScenarioExecRecorder(session.output_dir / f"{context_id}.jsonl", context_id, session)
    session.save()
    return recorder


def test_recording_session_rejects_file_output_directory(tmp_path):
    output = tmp_path / "output"
    output.write_text("existing file")
    with pytest.raises(FileExistsError):
        _session(output)
    assert output.read_text() == "existing file"


def test_recording_session_refuses_existing_dataset(tmp_path):
    path = tmp_path / "execution.trig"
    path.write_text("existing evidence")
    with pytest.raises(FileExistsError):
        _session(tmp_path)
    assert path.read_text() == "existing evidence"


@pytest.mark.parametrize("dataset_format", list(DatasetFormat))
def test_dataset_formats_preserve_shared_model_and_execution_bundles(tmp_path, dataset_format):
    model = Graph()
    model.add((URIRef("urn:model"), RDF.type, URIRef("urn:Model")))
    config = {"parameters": {"use_sim_time": False}}
    session = RecordingSession(
        tmp_path, AGENT, use_sim_time=False, dataset_format=dataset_format, config=config
    )
    session.model_graph.__iadd__(model)
    assert session.model_graph.identifier == session.model_id
    assert session.prov_bundle.identifier == session.prov_id
    assert session.model_graph.store is session.dataset.store
    assert session.prov_bundle.store is session.dataset.store
    recorders = [_open_recorder(session) for _ in range(2)]
    restored = Dataset().parse(session.path, format=dataset_format)
    assert session.path.name == f"execution.{dataset_format.extension}"
    assert set(restored.graph(session.model_id)) == set(model)
    bundle = restored.graph(session.prov_id)
    (snapshot,) = bundle.objects(session.config_id, PROV.value)
    assert json.loads(str(snapshot)) == config
    assert set(bundle.subjects(PROV.value, None)) == {session.config_id}
    for recorder in recorders:
        assert (
            recorder.bundle_id,
            PROV.wasGeneratedBy,
            recorder.execution_id,
        ) in restored.default_graph
        graph = restored.graph(recorder.bundle_id)
        assert (recorder.bundle_id, RDF.type, PROV.Bundle) in graph
        assert (recorder.execution_id, RDF.type, PROV.Activity) in graph
        assert (recorder.execution_id, PROV.used, session.config_id) in graph
        recorder.close()
    with pytest.raises(FileExistsError):
        _session(tmp_path, model, dataset_format=DatasetFormat.JSON_LD)


def test_session_save_failure_preserves_existing_dataset(tmp_path):
    from unittest.mock import patch

    session = _session(tmp_path)
    session.save()
    before = session.path.read_bytes()
    with (
        patch.object(session.dataset, "serialize", side_effect=OSError("disk full")),
        pytest.raises(OSError),
    ):
        session.save()
    assert session.path.read_bytes() == before


def test_graph_updates_do_not_implicitly_save_the_dataset(journal):
    from unittest.mock import patch

    writer, _ = journal
    with patch.object(writer.session, "save") as save:
        writer.record_policy_config(_policy())
        writer.record_metadata(POLICY, {"setting": True})
        save.assert_not_called()


def test_callback_links_configuration_samples_and_direct_results(journal):
    recorder, path = journal
    policy, direct = _policy(), _policy(evaluated=False)
    sample = ObservationStamped(URIRef("urn:observation"), URIRef("urn:provider"), 0.0, object())
    evidence = init_sample_details([sample])
    for item in (policy, direct):
        recorder.record_policy_config(item)
    recorder.session.save()
    recorder.record_policy_eval(policy, sample.stamp, Unknown, evidence)
    recorder.record_policy_eval(policy, sample.stamp, False, evidence)
    recorder.record_policy_eval(direct, sample.stamp, True, {})
    records = list(read_journal(path))
    sample_record, first, second, assertion = records
    dataset = Dataset().parse(recorder.session.path, format=recorder.session.dataset_format)
    configuration_id = URIRef(first["data"]["details"][ObsDetailKey.CONFIG_ID])
    graph = dataset.graph(recorder.bundle_id)
    assert (configuration_id, RDF.type, PROV.Entity) in graph
    assert (configuration_id, PROV.wasDerivedFrom, policy.id) in graph
    policy.evaluator.get_config.assert_called_once()
    assert sample_record["model_uri"] == sample.observation_uri
    for evaluation in (first, second):
        assert URIRef(evaluation["data"]["details"][ObsDetailKey.CONFIG_ID]) == configuration_id
        assert evaluation["data"]["details"][ObsDetailKey.SAMPLE_IDS] == [
            sample_record["data"]["sample_id"]
        ]
        assert evaluation["stamp"] == sample.stamp
    assert first["data"]["result"] == "unknown"
    assert second["data"]["result"] is False
    assert assertion["model_uri"] == direct.id
    assert assertion["data"] == {"result": True, "details": {}}
    assert ObsDetailKey.CONFIG_ID not in evidence


def test_configuration_changes_get_new_references(journal):
    recorder, path = journal
    policy = _policy()
    recorder.record_policy_config(policy)
    recorder.session.save()
    recorder.record_policy_eval(policy, 1.0, True, {})
    policy.evaluator.get_config.return_value = {"limit": 2.0}
    recorder.record_policy_config(policy)
    recorder.session.save()
    recorder.record_policy_eval(policy, 2.0, False, {})
    first_eval, second_eval = read_journal(path)
    first_id = URIRef(first_eval["data"]["details"][ObsDetailKey.CONFIG_ID])
    second_id = URIRef(second_eval["data"]["details"][ObsDetailKey.CONFIG_ID])
    assert first_id != second_id
    graph = (
        Dataset()
        .parse(recorder.session.path, format=recorder.session.dataset_format)
        .graph(recorder.bundle_id)
    )
    assert graph.value(first_id, PROV.value) != graph.value(second_id, PROV.value)


@pytest.mark.parametrize("config", [None, {}, {"nested": {"limit": 1.0}}])
def test_session_configuration_is_an_optional_shared_snapshot(tmp_path, config):
    session = RecordingSession(tmp_path, AGENT, use_sim_time=False, config=config)
    if config is None:
        assert session.config_id is None
        assert not list(session.prov_bundle.subjects(PROV.value, None))
        return
    assert (session.config_id, RDF.type, PROV.Entity) in session.prov_bundle
    assert (session.config_id, PROV.wasAttributedTo, AGENT) in session.prov_bundle
    value = session.prov_bundle.value(session.config_id, PROV.value)
    assert value.datatype == RDF.JSON
    assert json.loads(str(value)) == config
    config["later"] = True
    assert json.loads(str(value)) != config


def test_variable_assignments_preserve_values_and_execution_links(journal):
    from rdflib import Literal

    from bdd_dsl.models.namespace import NS_MM_BDD

    recorder, path = journal
    variable = URIRef("urn:variable")
    resource = URIRef("urn:resource")
    values = [resource, Literal(3), [], [resource, resource], (True, "label")]
    for value in values:
        recorder.record_var_assignments({variable: value})
    assignments = list(recorder.graph.subjects(RDF.type, NS_MM_BDD.VariableAssignment))
    assert len(assignments) == len(values)
    encoded = []
    for assignment in assignments:
        assert (assignment, RDF.type, PROV.Entity) in recorder.graph
        assert (recorder.execution_id, PROV.used, assignment) in recorder.graph
        assert list(recorder.graph.objects(assignment, NS_MM_BDD["ref-variable"])) == [variable]
        (value,) = recorder.graph.objects(assignment, RDF.value)
        encoded.append(value)
    assert resource in encoded and Literal(3) in encoded and RDF.nil in encoded
    collections = [
        list(recorder.graph.items(value)) for value in encoded if isinstance(value, BNode)
    ]
    assert [resource, resource] in collections
    assert [Literal(True), Literal("label")] in collections
    assert not path.read_bytes()


@pytest.mark.parametrize("value", [None, {}, {1}, object()])
def test_variable_assignments_reject_unsupported_values(journal, value):
    recorder, _ = journal
    with pytest.raises(TypeError):
        recorder.record_var_assignments({URIRef("urn:variable"): value})
