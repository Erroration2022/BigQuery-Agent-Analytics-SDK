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

"""Tests for drift table reference resolution."""

from unittest.mock import MagicMock

import pytest

from bigquery_agent_analytics.feedback import _GOLDEN_QUESTIONS_QUERY
from bigquery_agent_analytics.feedback import _PRODUCTION_QUESTIONS_QUERY
from bigquery_agent_analytics.feedback import _resolve_table_ref
from bigquery_agent_analytics.feedback import compute_drift


class TestResolveTableRef:
  """Tests for _resolve_table_ref."""

  def test_unqualified_table_uses_client_project_dataset(self):
    assert (
        _resolve_table_ref("agent_events", "proj", "ds")
        == "proj.ds.agent_events"
    )

  def test_fully_qualified_table_is_preserved(self):
    assert (
        _resolve_table_ref(
            "my_project.golden.qa_pairs_v3",
            "proj",
            "ds",
            param_name="golden_table",
        )
        == "my_project.golden.qa_pairs_v3"
    )

  def test_rejects_malformed_identifier(self):
    with pytest.raises(ValueError, match="golden_table"):
      _resolve_table_ref(
          "my_project.golden.qa`pairs",
          "proj",
          "ds",
          param_name="golden_table",
      )

  def test_rejects_partially_qualified_identifier(self):
    with pytest.raises(ValueError, match="table_id"):
      _resolve_table_ref("dataset.table", "proj", "ds")


class TestDriftQueriesUseResolvedRefs:
  """Drift SQL must not nest FQNs inside client project/dataset."""

  def test_golden_questions_query_uses_single_table_ref(self):
    sql = _GOLDEN_QUESTIONS_QUERY.format(
        golden_table_ref="my_project.golden.qa_pairs_v3",
    )
    assert "FROM `my_project.golden.qa_pairs_v3`" in sql
    assert "proj.ds.my_project" not in sql

  def test_production_questions_query_uses_single_table_ref(self):
    sql = _PRODUCTION_QUESTIONS_QUERY.format(
        table_ref="other_proj.trace.agent_events",
        where="TRUE",
    )
    assert "FROM `other_proj.trace.agent_events`" in sql


@pytest.mark.asyncio
async def test_compute_drift_uses_fully_qualified_golden_table():
  mock_bq = MagicMock()
  queries: list[str] = []

  def capture_query(query, job_config=None):
    queries.append(query)
    job = MagicMock()
    job.result.return_value = []
    return job

  mock_bq.query.side_effect = capture_query

  await compute_drift(
      bq_client=mock_bq,
      project_id="client_proj",
      dataset_id="client_ds",
      table_id="agent_events",
      golden_table="my_project.golden.qa_pairs_v3",
      where_clause="TRUE",
      query_params=[],
  )

  assert queries
  assert "FROM `my_project.golden.qa_pairs_v3`" in queries[0]
  assert "client_proj.client_ds.my_project" not in queries[0]
