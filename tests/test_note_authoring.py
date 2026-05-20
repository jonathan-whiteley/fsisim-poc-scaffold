from unittest.mock import MagicMock
from data_gen.note_authoring import NoteAuthor, IssueContext


def _fake_response(text: str):
    return MagicMock(choices=[MagicMock(message=MagicMock(content=text))])


def test_note_author_calls_serving_endpoint_with_context():
    fake_client = MagicMock()
    fake_client.serving_endpoints.query.return_value = _fake_response(
        "Hydraulic pressure dropped during takeoff. Replaced actuator seal."
    )

    author = NoteAuthor(client=fake_client, endpoint="databricks-claude-sonnet-4-5")
    ctx = IssueContext(
        issue_type="Mechanical", category="Hardware", systems="Hydraulics",
        root_cause="Worn actuator seal", sim_name="G001-SIM-01",
        sim_type_name="Full Flight Simulator", note_type="RES",
    )
    note = author.author(ctx)

    assert "Hydraulic" in note
    assert fake_client.serving_endpoints.query.called
    call_kwargs = fake_client.serving_endpoints.query.call_args.kwargs
    assert call_kwargs["name"] == "databricks-claude-sonnet-4-5"
    messages_repr = str(call_kwargs["messages"])
    assert "Hydraulics" in messages_repr
    assert "Worn actuator seal" in messages_repr
    assert "RES" in messages_repr or "Resolution" in messages_repr


def test_note_author_strips_quotes_and_whitespace():
    fake_client = MagicMock()
    fake_client.serving_endpoints.query.return_value = _fake_response(
        '  "Resolved by reseating the connector."  \n'
    )
    author = NoteAuthor(client=fake_client)
    ctx = IssueContext(
        issue_type="Electrical", category="Hardware", systems="Motion System",
        root_cause="Loose connector", sim_name="G001-SIM-03",
        sim_type_name="Fixed Training Device", note_type="RES",
    )
    note = author.author(ctx)
    assert note == "Resolved by reseating the connector."
