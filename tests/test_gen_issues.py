import random
from unittest.mock import MagicMock
from data_gen.gen_issues import IssueGenerator
from data_gen.value_domains import SIMULATORS


def test_generator_produces_requested_issue_count():
    fake_author = MagicMock()
    fake_author.author.return_value = "Mock note text."
    gen = IssueGenerator(seed=42, note_author=fake_author)
    issues = gen.generate(num_issues=10)
    issue_ids = {row.issue_id for row in issues}
    assert len(issue_ids) == 10


def test_generator_produces_one_to_four_notes_per_issue():
    fake_author = MagicMock()
    fake_author.author.return_value = "Mock note text."
    gen = IssueGenerator(seed=42, note_author=fake_author)
    issues = gen.generate(num_issues=20)
    by_issue: dict[int, int] = {}
    for row in issues:
        by_issue[row.issue_id] = by_issue.get(row.issue_id, 0) + 1
    for count in by_issue.values():
        assert 1 <= count <= 4


def test_generator_is_deterministic_with_seed():
    fake_author = MagicMock()
    fake_author.author.return_value = "Mock note text."
    gen1 = IssueGenerator(seed=42, note_author=fake_author)
    gen2 = IssueGenerator(seed=42, note_author=fake_author)
    issues1 = gen1.generate(num_issues=5)
    issues2 = gen2.generate(num_issues=5)
    assert [(r.issue_id, r.sim_name, r.root_cause, r.note_type) for r in issues1] == \
           [(r.issue_id, r.sim_name, r.root_cause, r.note_type) for r in issues2]


def test_every_issue_has_terminal_note():
    fake_author = MagicMock()
    fake_author.author.return_value = "Mock note text."
    gen = IssueGenerator(seed=7, note_author=fake_author)
    issues = gen.generate(num_issues=50)
    by_issue: dict[int, list[str]] = {}
    for row in issues:
        by_issue.setdefault(row.issue_id, []).append(row.note_type)
    for note_types in by_issue.values():
        assert note_types[-1] in ("SOL", "RES")


def test_generator_uses_known_simulators():
    fake_author = MagicMock()
    fake_author.author.return_value = "Mock note text."
    gen = IssueGenerator(seed=99, note_author=fake_author)
    issues = gen.generate(num_issues=30)
    known_names = {s.sim_name for s in SIMULATORS}
    for row in issues:
        assert row.sim_name in known_names
