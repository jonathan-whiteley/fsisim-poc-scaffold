-- Tools for FSISIM Issue Resolution Agent. Both UC functions wrap vector_search().
-- num_results is hardcoded inside each function because vector_search() requires
-- a foldable (compile-time constant) argument, and SQL UDF parameters are not
-- foldable. If you need different top-k at call time, define additional
-- variants (eg. search_past_issues_top10).
--
-- Substitutions handled by agent/apply_tools.py:
--   {catalog} {schema} {issue_index} {manual_index}

CREATE OR REPLACE FUNCTION {catalog}.{schema}.search_past_issues(
  query STRING COMMENT 'Natural language description of a simulator issue to search for.'
)
RETURNS TABLE(
  issue_id INT, issue_type STRING, systems STRING, sim_name STRING,
  note_type_description STRING, composite_text STRING, score DOUBLE
)
COMMENT 'Search past FSISIM issues by natural-language description. Returns top-5 similar past issues with their resolutions and structured metadata.'
RETURN
  SELECT issue_id, issue_type, systems, sim_name, note_type_description, composite_text, search_score AS score
  FROM vector_search(
    index => '{issue_index}',
    query => query,
    num_results => 5
  );

CREATE OR REPLACE FUNCTION {catalog}.{schema}.search_technical_manuals(
  query STRING COMMENT 'Term, acronym, or topic to look up in FSISIM technical manuals.'
)
RETURNS TABLE(
  source_pdf STRING, page_first INT, page_last INT,
  chunk_to_retrieve STRING, score DOUBLE
)
COMMENT 'Search FSISIM technical manuals for acronyms, system descriptions, fault codes, or procedural context. Returns top-3 chunks.'
RETURN
  SELECT source_pdf, page_first, page_last, chunk_to_retrieve, search_score AS score
  FROM vector_search(
    index => '{manual_index}',
    query => query,
    num_results => 3
  );
