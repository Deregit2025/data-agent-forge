"""
Tests for utils/multi_pass_retrieval.py

External calls (requests.post, OpenAI) are mocked so these tests
run without a live MCP server or OpenRouter API key.
"""

import pytest
from unittest.mock import patch, MagicMock
from utils.multi_pass_retrieval import retrieve, _execute, _broaden_query


# ── helpers ───────────────────────────────────────────────────────────────────

def _mcp_ok(rows: list, row_count: int | None = None) -> dict:
    """Build a fake successful MCP response."""
    return {
        "result":         rows,
        "row_count":      row_count if row_count is not None else len(rows),
        "query_used":     "SELECT 1",
        "db_type":        "sqlite",
        "tool_name":      "sqlite_query",
        "execution_time": 0.01,
    }


def _mcp_empty() -> dict:
    return _mcp_ok([], row_count=0)


def _mcp_error(msg: str = "connection refused") -> dict:
    return {
        "result":         [],
        "row_count":      0,
        "query_used":     "",
        "db_type":        "sqlite",
        "tool_name":      "sqlite_query",
        "execution_time": 0,
        "error":          msg,
    }


# ── _execute ──────────────────────────────────────────────────────────────────

class TestExecute:
    def test_success_sql_payload(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mcp_ok([{"id": 1}])
        mock_resp.raise_for_status.return_value = None

        with patch("utils.multi_pass_retrieval.requests.post", return_value=mock_resp) as mock_post:
            result = _execute("sqlite_query", "SELECT 1", "sqlite")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        # SQL tools use "sql" key in payload
        assert "sql" in call_kwargs.kwargs["json"] or "sql" in call_kwargs[1]["json"]
        assert result["row_count"] == 1

    def test_success_mongodb_payload(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mcp_ok([{"_id": "x"}])
        mock_resp.raise_for_status.return_value = None

        with patch("utils.multi_pass_retrieval.requests.post", return_value=mock_resp) as mock_post:
            result = _execute("mongo_query", "[{$match: {}}]", "mongodb")

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        # MongoDB tools use "pipeline" key
        assert "pipeline" in payload

    def test_network_error_returns_error_dict(self):
        with patch("utils.multi_pass_retrieval.requests.post", side_effect=ConnectionError("refused")):
            result = _execute("sqlite_query", "SELECT 1", "sqlite")

        assert result["row_count"] == 0
        assert "error" in result
        assert "refused" in result["error"]


# ── retrieve — pass routing ───────────────────────────────────────────────────

SCHEMA = {"tables": [{"name": "users", "columns": ["id", "name"]}]}

class TestRetrieve:
    def test_first_pass_succeeds_no_further_calls(self):
        """If pass 1 returns rows, stop immediately."""
        good = _mcp_ok([{"id": 1}, {"id": 2}])

        with patch("utils.multi_pass_retrieval._execute", return_value=good) as mock_exec:
            result = retrieve(
                tool_name="sqlite_query",
                query="SELECT * FROM users",
                db_type="sqlite",
                task="get all users",
                schema=SCHEMA,
            )

        assert mock_exec.call_count == 1
        assert result["row_count"] == 2
        assert result["total_passes"] == 1

    def test_first_pass_empty_triggers_second_pass(self):
        """Pass 1 empty → broaden → pass 2 succeeds."""
        good = _mcp_ok([{"id": 99}])
        responses = [_mcp_empty(), good]

        with patch("utils.multi_pass_retrieval._execute", side_effect=responses):
            with patch("utils.multi_pass_retrieval._broaden_query", return_value="SELECT * FROM users LIMIT 100"):
                result = retrieve(
                    tool_name="sqlite_query",
                    query="SELECT * FROM users WHERE name = 'Alice'",
                    db_type="sqlite",
                    task="find Alice",
                    schema=SCHEMA,
                )

        assert result["total_passes"] == 2
        assert result["row_count"] == 1

    def test_all_passes_empty_returns_last_result(self):
        """When all passes return 0 rows, return the last pass result."""
        with patch("utils.multi_pass_retrieval._execute", return_value=_mcp_empty()):
            with patch("utils.multi_pass_retrieval._broaden_query", return_value="SELECT 1"):
                result = retrieve(
                    tool_name="sqlite_query",
                    query="SELECT * FROM missing_table",
                    db_type="sqlite",
                    task="find something",
                    schema=SCHEMA,
                    max_passes=3,
                )

        assert result["row_count"] == 0
        assert result["total_passes"] == 3
        assert "passes" in result
        assert len(result["passes"]) == 3

    def test_passes_list_has_pass_numbers(self):
        """Each entry in passes[] must carry a pass_num."""
        good = _mcp_ok([{"x": 1}])
        with patch("utils.multi_pass_retrieval._execute", return_value=good):
            result = retrieve("t", "SELECT 1", "sqlite", "task", SCHEMA)

        for i, p in enumerate(result["passes"], start=1):
            assert p["pass_num"] == i

    def test_broaden_query_returning_empty_string_stops_loop(self):
        """If _broaden_query returns '', retrieval should stop early."""
        with patch("utils.multi_pass_retrieval._execute", return_value=_mcp_empty()):
            with patch("utils.multi_pass_retrieval._broaden_query", return_value=""):
                result = retrieve("t", "SELECT 1", "sqlite", "task", SCHEMA, max_passes=3)

        # stopped after pass 1 because broaden returned ""
        assert result["total_passes"] == 1

    def test_max_passes_one_only_runs_once(self):
        with patch("utils.multi_pass_retrieval._execute", return_value=_mcp_empty()) as mock_exec:
            with patch("utils.multi_pass_retrieval._broaden_query", return_value="SELECT 1"):
                retrieve("t", "SELECT 1", "sqlite", "task", SCHEMA, max_passes=1)

        assert mock_exec.call_count == 1

    def test_error_on_first_pass_triggers_broadening(self):
        """An error result (row_count=0 + error key) should also trigger pass 2."""
        responses = [_mcp_error("syntax error"), _mcp_ok([{"id": 7}])]
        with patch("utils.multi_pass_retrieval._execute", side_effect=responses):
            with patch("utils.multi_pass_retrieval._broaden_query", return_value="SELECT id FROM users"):
                result = retrieve("t", "BAD SQL", "sqlite", "task", SCHEMA)

        assert result["total_passes"] == 2
        assert result["row_count"] == 1


# ── _broaden_query (Claude call mocked) ──────────────────────────────────────

class TestBroadenQuery:
    def test_returns_cleaned_query(self):
        """_broaden_query should strip markdown fences from Claude response."""
        mock_choice = MagicMock()
        mock_choice.message.content = "```sql\nSELECT * FROM users\n```"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("utils.multi_pass_retrieval.get_client", return_value=mock_client):
            q = _broaden_query("SELECT 1", "sqlite", "find all", SCHEMA, "", pass_num=1, error="")

        assert "```" not in q
        assert "SELECT" in q

    def test_returns_empty_string_on_exception(self):
        """If Claude raises, return empty string so the caller can stop early."""
        with patch("utils.multi_pass_retrieval.get_client", side_effect=Exception("no key")):
            q = _broaden_query("SELECT 1", "sqlite", "task", SCHEMA, "", pass_num=1, error="")

        assert q == ""
