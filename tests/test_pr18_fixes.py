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

"""Tests for PR #18 fixes.

Covers:
  - Biz-node MERGE skips delete when AI extraction returns zero rows
  - Decision edge creation uses atomic MERGE instead of delete-then-insert
"""

from __future__ import annotations

from unittest.mock import MagicMock

from bigquery_agent_analytics.context_graph import (
    _EXTRACT_BIZ_NODES_QUERY,
    _MERGE_CANDIDATE_EDGES_QUERY,
    _MERGE_MADE_DECISION_EDGES_QUERY,
    ContextGraphManager,
)


class TestBizNodeMergeEmptyExtractionGuard:
  """Biz-node stale cleanup must not run when extraction is empty."""

  def test_merge_delete_scoped_to_nonempty_source_sessions(self):
    assert (
        "target.session_id IN (SELECT DISTINCT session_id FROM source)"
        in _EXTRACT_BIZ_NODES_QUERY
    )
    assert "target.session_id IN UNNEST(@session_ids)" not in _EXTRACT_BIZ_NODES_QUERY


class TestDecisionEdgeMergeTemplates:
  """Decision edges use MERGE upserts with safe stale-row cleanup."""

  def test_made_decision_edges_use_merge(self):
    assert "MERGE" in _MERGE_MADE_DECISION_EDGES_QUERY
    assert (
        "target.decision_id IN (SELECT DISTINCT decision_id FROM source)"
        in _MERGE_MADE_DECISION_EDGES_QUERY
    )

  def test_candidate_edges_use_merge(self):
    assert "MERGE" in _MERGE_CANDIDATE_EDGES_QUERY
    assert (
        "target.decision_id IN (SELECT DISTINCT decision_id FROM source)"
        in _MERGE_CANDIDATE_EDGES_QUERY
    )

  def test_create_decision_edges_uses_merge_queries(self):
    mock_client = MagicMock()
    mock_job = MagicMock()
    mock_client.query.return_value = mock_job
    mgr = ContextGraphManager(
        project_id="test-project",
        dataset_id="test_dataset",
        table_id="agent_events",
        client=mock_client,
    )

    assert mgr.create_decision_edges(["sess-1"]) is True

    merge_calls = [str(call.args[0]) for call in mock_client.query.call_args_list]
    assert any("MERGE" in sql and "made_decision_edges" in sql for sql in merge_calls)
    assert any("MERGE" in sql and "candidate_edges" in sql for sql in merge_calls)
    assert not any(sql.strip().startswith("DELETE") for sql in merge_calls)
