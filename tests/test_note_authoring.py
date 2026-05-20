from unittest.mock import MagicMock
from data_gen.note_authoring import NoteAuthor, IssueContext


def test_note_author_calls_anthropic_with_context(monkeypatch):
    fake_client = MagicMock()
    fake_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Hydraulic pressure dropped during takeoff. Replaced actuator seal.")]
    )

    author = NoteAuthor(client=fake_client)
    ctx = IssueContext(
        issue_type="Mechanical", category="Hardware", systems="Hydraulics",
        root_cause="Worn actuator seal", sim_name="G001-SIM-01",
        sim_type_name="Full Flight Simulator", note_type="RES",
    )
    note = author.author(ctx)

    assert "Hydraulic" in note
    assert fake_client.messages.create.called
    call_kwargs = fake_client.messages.create.call_args.kwargs
    assert call_kwargs["model"].startswith("claude-")
    prompt = str(call_kwargs["messages"])
    assert "Hydraulics" in prompt
    assert "Worn actuator seal" in prompt
    assert "RES" in prompt or "Resolution" in prompt


def test_note_author_strips_quotes_and_whitespace():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='  "Resolved by reseating the connector."  \n')]
    )
    author = NoteAuthor(client=fake_client)
    ctx = IssueContext(
        issue_type="Electrical", category="Hardware", systems="Motion System",
        root_cause="Loose connector", sim_name="G001-SIM-03",
        sim_type_name="Fixed Training Device", note_type="RES",
    )
    note = author.author(ctx)
    assert note == "Resolved by reseating the connector."
