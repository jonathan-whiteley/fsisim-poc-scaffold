"""Synthetic note text generator backed by the Databricks Foundation Model API.

Uses the workspace's databricks-claude-sonnet-4-5 endpoint (configurable via
FSISIM_LLM_ENDPOINT). No personal Anthropic key required: auth flows through
the user's Databricks profile.
"""
from dataclasses import dataclass
from typing import Optional

NOTE_TYPE_NAMES = {
    "INI": "Initial Report",
    "UPD": "Update",
    "SOL": "Solution",
    "RES": "Resolution",
}


@dataclass(frozen=True)
class IssueContext:
    issue_type: str
    category: str
    systems: str
    root_cause: str
    sim_name: str
    sim_type_name: str
    note_type: str


SYSTEM_PROMPT = (
    "You are writing a single short technical note for a flight simulator issue tracking system "
    "(FSISIM). Notes are written by maintenance technicians and engineers. Use realistic aviation "
    "and simulator jargon (APU, FMC, FMS, VNAV, ILS, IRS, EICAS, RA, IOS, BIT, fault code, etc. "
    "where appropriate). Keep notes to 1-3 sentences. No bullet points. No quotes. No preamble. "
    "Just the note text."
)


def _note_type_instruction(note_type: str) -> str:
    name = NOTE_TYPE_NAMES.get(note_type, note_type)
    if note_type == "INI":
        return f"Write an {name}: describe what went wrong, when it was first noticed, and any immediate action taken."
    if note_type == "UPD":
        return f"Write an {name}: status update on ongoing investigation, parts ordered, or troubleshooting attempted."
    if note_type == "SOL":
        return f"Write a {name}: describe the fix applied and confirmation it resolved the issue."
    if note_type == "RES":
        return f"Write a {name}: final closeout note confirming the issue is resolved and the simulator is back in service."
    return f"Write a {name} note."


class NoteAuthor:
    """Calls a Databricks serving endpoint to author one note per call.

    Default endpoint is `databricks-claude-sonnet-4-5`. Inject `client`
    (a databricks.sdk.WorkspaceClient or a duck-typed mock) for testing.
    """

    def __init__(self, client=None, endpoint: str = "databricks-claude-sonnet-4-5"):
        if client is None:
            from databricks.sdk import WorkspaceClient
            client = WorkspaceClient()
        self.client = client
        self.endpoint = endpoint

    def author(self, ctx: IssueContext) -> str:
        from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

        user_msg = (
            f"Issue type: {ctx.issue_type}\n"
            f"Category: {ctx.category}\n"
            f"System: {ctx.systems}\n"
            f"Root cause: {ctx.root_cause}\n"
            f"Simulator: {ctx.sim_name} ({ctx.sim_type_name})\n"
            f"Note type code: {ctx.note_type} ({NOTE_TYPE_NAMES.get(ctx.note_type, ctx.note_type)})\n\n"
            f"{_note_type_instruction(ctx.note_type)}"
        )
        resp = self.client.serving_endpoints.query(
            name=self.endpoint,
            messages=[
                ChatMessage(role=ChatMessageRole.SYSTEM, content=SYSTEM_PROMPT),
                ChatMessage(role=ChatMessageRole.USER, content=user_msg),
            ],
            max_tokens=200,
        )
        text = resp.choices[0].message.content.strip()
        return text.strip('"').strip()
