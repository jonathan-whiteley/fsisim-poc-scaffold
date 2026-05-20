"""Synthetic g001_issue row generator. Note-grain; multiple notes per issue."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
import random
from typing import Optional, Sequence
from data_gen.note_authoring import IssueContext, NoteAuthor
from data_gen.value_domains import (
    ISSUE_TYPES, ISSUE_TYPE_WEIGHTS, CATEGORIES_BY_TYPE, SYSTEMS_BY_TYPE,
    ROOT_CAUSES, LOST_TIME_TYPES, LOST_TIME_TYPE_WEIGHTS, NOTE_TYPES,
    NOTE_CREATORS, ISSUE_CATEGORIES, ISSUE_CATEGORY_WEIGHTS, DEVICE_STATUSES,
    SIMULATORS, SimulatorRecord,
)


@dataclass
class IssueRow:
    id: str
    issue_id: int
    issue_type: str
    issue_create_date: datetime
    category: str
    mmi: bool
    systems: str
    root_cause: str
    due_date_comment: Optional[str]
    lost_time: float
    lost_time_type: str
    sim_id: int
    sim_name: str
    sim_type: int
    sim_type_name: str
    loc_name: str
    sim_location_id: int
    note: str
    note_type: str
    note_type_description: str
    note_name_creator: str
    note_create_date: datetime
    issue_category: str
    assign_type: int
    device_id: int
    device_status: str
    sim_lead_location_id: int
    lead_loc_name: str

    def as_row_tuple(self) -> tuple:
        return tuple(asdict(self).values())


def _wchoice(rng: random.Random, items: Sequence[str], weights: Sequence[float]) -> str:
    return rng.choices(items, weights=weights, k=1)[0]


def _build_note_sequence(rng: random.Random) -> list[tuple[str, str]]:
    """Realistic arc: INI -> [UPD]* -> {SOL or RES}. Length 1-4."""
    extras = rng.choices([0, 1, 2], weights=[0.50, 0.35, 0.15], k=1)[0]
    terminal = ("SOL", "Solution") if rng.random() < 0.45 else ("RES", "Resolution")
    seq = [("INI", "Initial Report")]
    seq.extend([("UPD", "Update")] * extras)
    seq.append(terminal)
    if len(seq) == 1:
        seq = [terminal]
    return seq


class IssueGenerator:
    def __init__(self, seed: int = 42, note_author: Optional[NoteAuthor] = None):
        self.rng = random.Random(seed)
        self.note_author = note_author or NoteAuthor()

    def generate(self, num_issues: int) -> list[IssueRow]:
        rows: list[IssueRow] = []
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=730)
        for i in range(num_issues):
            issue_id = 1001 + i
            issue_type = _wchoice(self.rng, ISSUE_TYPES, ISSUE_TYPE_WEIGHTS)
            category = self.rng.choice(CATEGORIES_BY_TYPE[issue_type])
            systems = self.rng.choice(SYSTEMS_BY_TYPE[issue_type])
            root_cause = self.rng.choice(ROOT_CAUSES)
            sim: SimulatorRecord = self.rng.choice(SIMULATORS)
            issue_create = window_start + timedelta(
                seconds=self.rng.randint(0, int((now - window_start).total_seconds()))
            )
            lost_time_type = _wchoice(self.rng, LOST_TIME_TYPES, LOST_TIME_TYPE_WEIGHTS)
            lost_time = 0.0 if lost_time_type == "Non-Impact" else round(self.rng.uniform(0.5, 8.0), 1)
            mmi = self.rng.random() < 0.55
            due_comment = self.rng.choice([None, "Parts on order", "Expedited repair", "Pending vendor response"])
            issue_category = _wchoice(self.rng, ISSUE_CATEGORIES, ISSUE_CATEGORY_WEIGHTS)
            assign_type = self.rng.choice([1, 2, 3])
            device_id = 3000 + (sim.sim_id % 100)
            device_status = self.rng.choice(DEVICE_STATUSES)

            note_seq = _build_note_sequence(self.rng)
            cursor = issue_create
            for n_idx, (nt_code, nt_desc) in enumerate(note_seq):
                cursor = cursor + timedelta(hours=self.rng.randint(1, 36))
                note_text = self.note_author.author(IssueContext(
                    issue_type=issue_type, category=category, systems=systems,
                    root_cause=root_cause, sim_name=sim.sim_name,
                    sim_type_name=sim.sim_type_name, note_type=nt_code,
                ))
                rows.append(IssueRow(
                    id=f"note-{issue_id:05d}-{n_idx+1:02d}",
                    issue_id=issue_id,
                    issue_type=issue_type,
                    issue_create_date=issue_create,
                    category=category,
                    mmi=mmi,
                    systems=systems,
                    root_cause=root_cause,
                    due_date_comment=due_comment,
                    lost_time=lost_time,
                    lost_time_type=lost_time_type,
                    sim_id=sim.sim_id,
                    sim_name=sim.sim_name,
                    sim_type=sim.sim_type,
                    sim_type_name=sim.sim_type_name,
                    loc_name=sim.loc_name,
                    sim_location_id=sim.sim_location_id,
                    note=note_text,
                    note_type=nt_code,
                    note_type_description=nt_desc,
                    note_name_creator=self.rng.choice(NOTE_CREATORS),
                    note_create_date=cursor,
                    issue_category=issue_category,
                    assign_type=assign_type,
                    device_id=device_id,
                    device_status=device_status,
                    sim_lead_location_id=sim.sim_location_id,
                    lead_loc_name=sim.loc_name,
                ))
        return rows
