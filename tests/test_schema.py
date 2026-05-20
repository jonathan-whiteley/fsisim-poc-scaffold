from data_gen.schema import G001_ISSUE_SCHEMA, EXPECTED_COLUMNS


def test_schema_has_28_fields():
    assert len(G001_ISSUE_SCHEMA.fields) == 28


def test_column_names_match_gold_spec():
    actual = [f.name for f in G001_ISSUE_SCHEMA.fields]
    assert actual == EXPECTED_COLUMNS


def test_mmi_is_boolean():
    f = next(f for f in G001_ISSUE_SCHEMA.fields if f.name == "mmi")
    assert f.dataType.simpleString() == "boolean"


def test_lost_time_is_double():
    f = next(f for f in G001_ISSUE_SCHEMA.fields if f.name == "lost_time")
    assert f.dataType.simpleString() == "double"


def test_issue_create_date_is_timestamp():
    f = next(f for f in G001_ISSUE_SCHEMA.fields if f.name == "issue_create_date")
    assert f.dataType.simpleString() == "timestamp"
