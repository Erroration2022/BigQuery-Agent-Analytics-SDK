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

"""Tests that session-level LIMIT clauses use deterministic recency ordering."""

from bigquery_agent_analytics.ai_ml_integration import BatchEvaluator
from bigquery_agent_analytics.categorical_evaluator import (
    build_ai_classify_query,
    build_ai_generate_query,
    CATEGORICAL_AI_GENERATE_QUERY,
    CATEGORICAL_TRANSCRIPT_QUERY,
)
from bigquery_agent_analytics.client import _LIST_TRACES_QUERY
from bigquery_agent_analytics.evaluators import (
    AI_GENERATE_JUDGE_BATCH_QUERY,
    LLM_JUDGE_BATCH_QUERY,
    SESSION_SUMMARY_QUERY,
)


class TestSessionLimitOrdering:
  """Session sampling must order by recency before LIMIT."""

  def test_session_summary_query_orders_before_limit(self):
    limit_idx = SESSION_SUMMARY_QUERY.index("LIMIT @trace_limit")
    order_idx = SESSION_SUMMARY_QUERY.index("ORDER BY MAX(timestamp) DESC")
    assert order_idx < limit_idx

  def test_list_traces_query_orders_sessions_by_recency(self):
    assert "ORDER BY MAX(timestamp) DESC" in _LIST_TRACES_QUERY
    assert "SELECT DISTINCT session_id" not in _LIST_TRACES_QUERY

  def test_judge_batch_queries_order_before_limit(self):
    for query in (AI_GENERATE_JUDGE_BATCH_QUERY, LLM_JUDGE_BATCH_QUERY):
      limit_idx = query.index("LIMIT @trace_limit")
      order_idx = query.index("ORDER BY MAX(timestamp) DESC")
      assert order_idx < limit_idx

  def test_categorical_templates_order_before_limit(self):
    for query in (CATEGORICAL_TRANSCRIPT_QUERY, CATEGORICAL_AI_GENERATE_QUERY):
      limit_idx = query.index("LIMIT @trace_limit")
      order_idx = query.index("ORDER BY MAX(timestamp) DESC")
      assert order_idx < limit_idx

  def test_categorical_query_builders_order_before_limit(self):
    classify_query = build_ai_classify_query(
        config=_minimal_config(),
        project="p",
        dataset="d",
        table="t",
        where="TRUE",
        endpoint="gemini-2.5-flash",
    )
    generate_query = build_ai_generate_query(
        project="p",
        dataset="d",
        table="t",
        where="TRUE",
        endpoint="gemini-2.5-flash",
        temperature=0.1,
    )
    for query in (classify_query, generate_query):
      limit_idx = query.index("LIMIT @trace_limit")
      order_idx = query.index("ORDER BY MAX(timestamp) DESC")
      assert order_idx < limit_idx

  def test_batch_evaluator_queries_order_before_limit(self):
    for query in (
        BatchEvaluator._BATCH_EVALUATION_QUERY,
        BatchEvaluator._LEGACY_BATCH_EVALUATION_QUERY,
    ):
      limit_idx = query.index("LIMIT @limit")
      order_idx = query.index("ORDER BY MAX(timestamp) DESC")
      assert order_idx < limit_idx


def _minimal_config():
  from bigquery_agent_analytics.categorical_evaluator import (
      CategoricalEvaluationConfig,
      CategoricalMetricCategory,
      CategoricalMetricDefinition,
  )

  return CategoricalEvaluationConfig(
      metrics=[
          CategoricalMetricDefinition(
              name="intent",
              definition="User intent",
              categories=[
                  CategoricalMetricCategory(
                      name="search",
                      definition="Search intent",
                  ),
                  CategoricalMetricCategory(
                      name="other",
                      definition="Other intent",
                  ),
              ],
          )
      ]
  )
