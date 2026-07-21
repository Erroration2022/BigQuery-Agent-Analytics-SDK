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

"""Validation helpers for SQL identifier interpolation."""

from __future__ import annotations

import re

_TABLE_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_VIEW_PREFIX_RE = re.compile(r"^[A-Za-z0-9_]*$")


def validate_table_id(table_id: str, *, param_name: str = "table_id") -> str:
  """Validate an unqualified BigQuery table identifier.

  Several SDK code paths embed table names directly into DDL/DML SQL.
  Reject values that could break out of backtick-quoted references.
  """
  if not table_id or not _TABLE_ID_RE.fullmatch(table_id):
    raise ValueError(
        f"Invalid {param_name}: {table_id!r}. Must be an unqualified "
        "table name containing only letters, numbers, and underscores."
    )
  return table_id


def validate_view_prefix(prefix: str) -> str:
  """Validate a view-name prefix used before a fixed suffix."""
  if not _VIEW_PREFIX_RE.fullmatch(prefix):
    raise ValueError(
        f"Invalid view_prefix: {prefix!r}. Must contain only letters, "
        "numbers, and underscores."
    )
  return prefix
