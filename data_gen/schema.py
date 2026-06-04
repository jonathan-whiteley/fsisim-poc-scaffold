"""PySpark schema for poc_data.fsisim_issue_ai_gold.g001_issue.

Gold schema (28 columns, note-grain) for the FSISIM issue records.
"""
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    TimestampType, BooleanType, DoubleType,
)

EXPECTED_COLUMNS = [
    "id", "issue_id", "issue_type", "issue_create_date", "category", "mmi",
    "systems", "root_cause", "due_date_comment", "lost_time", "lost_time_type",
    "sim_id", "sim_name", "sim_type", "sim_type_name", "loc_name",
    "sim_location_id", "note", "note_type", "note_type_description",
    "note_name_creator", "note_create_date", "issue_category", "assign_type",
    "device_id", "device_status", "sim_lead_location_id", "lead_loc_name",
]

G001_ISSUE_SCHEMA = StructType([
    StructField("id", StringType(), True),
    StructField("issue_id", IntegerType(), True),
    StructField("issue_type", StringType(), True),
    StructField("issue_create_date", TimestampType(), True),
    StructField("category", StringType(), True),
    StructField("mmi", BooleanType(), True),
    StructField("systems", StringType(), True),
    StructField("root_cause", StringType(), True),
    StructField("due_date_comment", StringType(), True),
    StructField("lost_time", DoubleType(), True),
    StructField("lost_time_type", StringType(), True),
    StructField("sim_id", IntegerType(), True),
    StructField("sim_name", StringType(), True),
    StructField("sim_type", IntegerType(), True),
    StructField("sim_type_name", StringType(), True),
    StructField("loc_name", StringType(), True),
    StructField("sim_location_id", IntegerType(), True),
    StructField("note", StringType(), True),
    StructField("note_type", StringType(), True),
    StructField("note_type_description", StringType(), True),
    StructField("note_name_creator", StringType(), True),
    StructField("note_create_date", TimestampType(), True),
    StructField("issue_category", StringType(), True),
    StructField("assign_type", IntegerType(), True),
    StructField("device_id", IntegerType(), True),
    StructField("device_status", StringType(), True),
    StructField("sim_lead_location_id", IntegerType(), True),
    StructField("lead_loc_name", StringType(), True),
])
