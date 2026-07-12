# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for session-level has_error filtering and endpoint SQL escaping."""

from bigquery_agent_analytics.client import _LIST_TRACES_QUERY
from bigquery_agent_analytics.evaluators import AI_GENERATE_JUDGE_BATCH_QUERY
from bigquery_agent_analytics.evaluators import SESSION_SUMMARY_QUERY
from bigquery_agent_analytics.insights import _SESSION_METADATA_QUERY
from bigquery_agent_analytics.trace import escape_sql_string_literal
from bigquery_agent_analytics.trace import TraceFilter
from bigquery_agent_analytics.trace import session_error_having_clause
from bigquery_agent_analytics.trace import session_error_having_suffix


class TestSessionErrorFilter:
  """has_error must filter sessions, not individual event rows."""

  def test_has_error_not_in_row_where_clause(self):
    filt = TraceFilter(has_error=False)
    where, _ = filt.to_sql_conditions()
    assert "ENDS_WITH(event_type, '_ERROR')" not in where

  def test_no_error_uses_session_having(self):
    filt = TraceFilter(has_error=False)
    having = filt.session_error_having()
    assert having.startswith("HAVING ")
    assert "= 0" in having

  def test_with_error_uses_session_having(self):
    filt = TraceFilter(has_error=True)
    having = filt.session_error_having()
    assert having.startswith("HAVING ")
    assert "> 0" in having

  def test_having_suffix_for_existing_clause(self):
    suffix = session_error_having_suffix(False)
    assert suffix.startswith(" AND COUNTIF(")
    assert "= 0" in suffix

  def test_list_traces_query_groups_before_limit(self):
    query = _LIST_TRACES_QUERY.format(
        project="p",
        dataset="d",
        table="events",
        where="TRUE",
        session_having=session_error_having_clause(False),
    )
    assert "GROUP BY session_id" in query
    assert "HAVING COUNTIF(ENDS_WITH(event_type, '_ERROR')" in query
    assert "SELECT DISTINCT session_id" not in query

  def test_session_summary_query_uses_session_having(self):
    query = SESSION_SUMMARY_QUERY.format(
        project="p",
        dataset="d",
        table="events",
        where="TRUE",
        session_having=session_error_having_clause(False),
    )
    assert "GROUP BY session_id" in query
    assert "HAVING COUNTIF(ENDS_WITH(event_type, '_ERROR')" in query

  def test_judge_query_appends_session_having_to_existing_having(self):
    query = AI_GENERATE_JUDGE_BATCH_QUERY.format(
        project="p",
        dataset="d",
        table="events",
        where="TRUE",
        endpoint="gemini-2.5-flash",
        session_having_and=session_error_having_suffix(False),
    )
    assert "HAVING LENGTH(trace_text) > 10 AND COUNTIF(" in query

  def test_insights_metadata_query_appends_session_having(self):
    query = _SESSION_METADATA_QUERY.format(
        project="p",
        dataset="d",
        table="events",
        where="TRUE",
        session_having_and=session_error_having_suffix(True),
    )
    assert "AND turn_count >= @min_turns AND COUNTIF(" in query.replace("\n", " ")


class TestEndpointSqlEscaping:
  def test_escape_sql_string_literal_doubles_quotes(self):
    assert escape_sql_string_literal("a'b") == "a''b"

  def test_judge_query_escapes_endpoint(self):
    endpoint = "gemini-2.5-flash', output_schema => 'score INT64"
    query = AI_GENERATE_JUDGE_BATCH_QUERY.format(
        project="p",
        dataset="d",
        table="events",
        where="TRUE",
        endpoint=escape_sql_string_literal(endpoint),
        session_having_and="",
    )
    assert "endpoint => 'gemini-2.5-flash'', output_schema => ''score INT64'" in query
