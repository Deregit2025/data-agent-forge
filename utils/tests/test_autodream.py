"""
Tests for utils/autodream.py

Filesystem operations use tmp_path (pytest fixture) so nothing touches
the real kb/ directory. Claude/OpenAI calls are mocked throughout.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from utils.autodream import parse_corrections, log_correction, consolidate, _update_changelog


# ── parse_corrections ─────────────────────────────────────────────────────────

class TestParseCorrections:
    def test_empty_text_returns_empty_list(self):
        assert parse_corrections("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert parse_corrections("   \n\n  ") == []

    def test_single_well_formed_entry(self):
        text = """
## yelp — 2026-04-10
**Query:** What is the average rating for businesses in Nevada?
**What was wrong:** Used state full name 'Nevada' but the column stores abbreviation 'NV'
**Correct approach:** Filter using state = 'NV' not 'Nevada'
**Failure type:** DATA_TYPE_ERROR
"""
        entries = parse_corrections(text)
        assert len(entries) == 1
        e = entries[0]
        assert e["dataset"] == "yelp"
        assert "Nevada" in e["query"]
        assert "'Nevada'" in e["what_was_wrong"]
        assert "'NV'" in e["correct_approach"]
        assert e["failure_type"] == "DATA_TYPE_ERROR"

    def test_multiple_entries_parsed_correctly(self):
        text = """
## yelp — 2026-04-09
**Query:** Count businesses in Indiana
**What was wrong:** State stored as 'IN' not 'Indiana'
**Correct approach:** Use state = 'IN'
**Failure type:** DATA_TYPE_ERROR

## bookreview — 2026-04-10
**Query:** Find top rated books
**What was wrong:** Used bookid_ prefix instead of purchaseid_
**Correct approach:** Translate bookid_ to purchaseid_ before joining
**Failure type:** JOIN_KEY_MISMATCH
"""
        entries = parse_corrections(text)
        assert len(entries) == 2
        datasets = {e["dataset"] for e in entries}
        assert "yelp" in datasets
        assert "bookreview" in datasets

    def test_entry_without_query_field_excluded(self):
        # a block with no **Query:** line should be skipped
        text = """
## yelp — 2026-04-10
**What was wrong:** Something
**Correct approach:** Do this instead
**Failure type:** UNKNOWN
"""
        entries = parse_corrections(text)
        assert len(entries) == 0

    def test_partial_fields_still_parsed(self):
        # query present, other fields missing — entry still included
        # the regex captures the full word including underscores
        text = """
## music_brainz — 2026-04-10
**Query:** List all artists from Germany
"""
        entries = parse_corrections(text)
        assert len(entries) == 1
        assert entries[0]["dataset"] == "music_brainz"
        assert "Germany" in entries[0]["query"]

    def test_raw_block_preserved(self):
        text = """
## yelp — 2026-04-10
**Query:** Something
**What was wrong:** X
**Correct approach:** Y
**Failure type:** Z
"""
        entries = parse_corrections(text)
        assert "raw" in entries[0]


# ── log_correction ────────────────────────────────────────────────────────────

class TestLogCorrection:
    def test_creates_file_and_writes_entry(self, tmp_path):
        corrections_file = tmp_path / "corrections" / "corrections_log.md"

        with patch("utils.autodream.CORRECTIONS", corrections_file):
            log_correction(
                dataset="yelp",
                query="How many 5-star businesses are in Nevada?",
                what_was_wrong="Used full state name instead of abbreviation",
                correct_approach="Use state = 'NV'",
                failure_type="DATA_TYPE_ERROR",
            )

        assert corrections_file.exists()
        content = corrections_file.read_text(encoding="utf-8")
        assert "## yelp" in content
        assert "How many 5-star" in content
        assert "DATA_TYPE_ERROR" in content

    def test_appends_multiple_entries(self, tmp_path):
        corrections_file = tmp_path / "corrections" / "corrections_log.md"

        with patch("utils.autodream.CORRECTIONS", corrections_file):
            log_correction("yelp", "Q1", "W1", "C1", "UNKNOWN")
            log_correction("bookreview", "Q2", "W2", "C2", "JOIN_KEY_MISMATCH")

        content = corrections_file.read_text(encoding="utf-8")
        assert "## yelp" in content
        assert "## bookreview" in content
        assert content.index("## yelp") < content.index("## bookreview")

    def test_entry_contains_all_fields(self, tmp_path):
        corrections_file = tmp_path / "corrections" / "corrections_log.md"

        with patch("utils.autodream.CORRECTIONS", corrections_file):
            log_correction(
                dataset="stockmarket",
                query="What was AAPL's closing price on 2024-01-15?",
                what_was_wrong="Table name was wrong",
                correct_approach="Use ticker-specific table aapl_stock",
                failure_type="SCHEMA_MISMATCH",
            )

        content = corrections_file.read_text(encoding="utf-8")
        assert "**Query:**" in content
        assert "**What was wrong:**" in content
        assert "**Correct approach:**" in content
        assert "**Failure type:**" in content
        assert "SCHEMA_MISMATCH" in content


# ── consolidate ───────────────────────────────────────────────────────────────

class TestConsolidate:
    def _make_domain_file(self, tmp_path: Path, dataset: str) -> Path:
        domain_dir = tmp_path / "domain"
        domain_dir.mkdir(parents=True, exist_ok=True)
        f = domain_dir / f"dab_{dataset}.md"
        f.write_text(f"# {dataset} knowledge base\n\nBasic info about {dataset}.", encoding="utf-8")
        return f

    def _make_corrections_file(self, tmp_path: Path, content: str) -> Path:
        corr_dir = tmp_path / "corrections"
        corr_dir.mkdir(parents=True, exist_ok=True)
        f = corr_dir / "corrections_log.md"
        f.write_text(content, encoding="utf-8")
        return f

    def test_no_corrections_file_exits_gracefully(self, tmp_path, capsys):
        missing = tmp_path / "corrections" / "corrections_log.md"
        with patch("utils.autodream.CORRECTIONS", missing):
            consolidate()  # should not raise

        out = capsys.readouterr().out
        assert "No corrections log found" in out

    def test_empty_corrections_file_exits_gracefully(self, tmp_path, capsys):
        corrections_file = self._make_corrections_file(tmp_path, "")
        with patch("utils.autodream.CORRECTIONS", corrections_file):
            consolidate()

        out = capsys.readouterr().out
        assert "empty" in out.lower()

    def test_no_parseable_entries_exits_gracefully(self, tmp_path, capsys):
        corrections_file = self._make_corrections_file(tmp_path, "Just some random text with no structure.")
        with patch("utils.autodream.CORRECTIONS", corrections_file):
            consolidate()

        out = capsys.readouterr().out
        assert "No parseable" in out

    def test_consolidate_calls_claude_and_writes_domain_file(self, tmp_path):
        corrections_text = """
## yelp — 2026-04-10
**Query:** Count businesses in Nevada
**What was wrong:** Used full state name
**Correct approach:** Use state = 'NV'
**Failure type:** DATA_TYPE_ERROR
"""
        corrections_file = self._make_corrections_file(tmp_path, corrections_text)
        domain_file = self._make_domain_file(tmp_path, "yelp")
        changelog_file = tmp_path / "domain" / "CHANGELOG.md"

        # mock Claude returning updated content
        mock_choice = MagicMock()
        mock_choice.message.content = "# yelp KB\n\n## Known Failure Patterns\n- Use 'NV' not 'Nevada'"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("utils.autodream.CORRECTIONS", corrections_file), \
             patch("utils.autodream.DOMAIN_DIR", tmp_path / "domain"), \
             patch("utils.autodream.get_client", return_value=mock_client):
            consolidate()

        updated = domain_file.read_text(encoding="utf-8")
        assert "Known Failure Patterns" in updated

    def test_consolidate_skips_unknown_dataset(self, tmp_path, capsys):
        corrections_text = """
## nonexistent_dataset — 2026-04-10
**Query:** Some query
**What was wrong:** Something
**Correct approach:** Something else
**Failure type:** UNKNOWN
"""
        corrections_file = self._make_corrections_file(tmp_path, corrections_text)
        # domain dir exists but has no file for this dataset
        domain_dir = tmp_path / "domain"
        domain_dir.mkdir(parents=True, exist_ok=True)

        with patch("utils.autodream.CORRECTIONS", corrections_file), \
             patch("utils.autodream.DOMAIN_DIR", domain_dir):
            consolidate()

        out = capsys.readouterr().out
        assert "SKIP" in out

    def test_consolidate_groups_multiple_entries_by_dataset(self, tmp_path):
        corrections_text = """
## yelp — 2026-04-10
**Query:** Query 1
**What was wrong:** Problem 1
**Correct approach:** Fix 1
**Failure type:** UNKNOWN

## yelp — 2026-04-11
**Query:** Query 2
**What was wrong:** Problem 2
**Correct approach:** Fix 2
**Failure type:** UNKNOWN
"""
        corrections_file = self._make_corrections_file(tmp_path, corrections_text)
        self._make_domain_file(tmp_path, "yelp")

        call_args_list = []

        def capture_update(dataset, corrections, existing):
            call_args_list.append((dataset, corrections))
            return existing  # return unchanged

        # patch DOMAIN_DIR so _update_changelog also writes to tmp_path, not real kb/
        with patch("utils.autodream.CORRECTIONS", corrections_file), \
             patch("utils.autodream.DOMAIN_DIR", tmp_path / "domain"), \
             patch("utils.autodream.update_domain_file", side_effect=capture_update), \
             patch("utils.autodream._update_changelog"):
            consolidate()

        # both yelp entries should be batched into one update_domain_file call
        assert len(call_args_list) == 1
        dataset, corrections = call_args_list[0]
        assert dataset == "yelp"
        assert len(corrections) == 2

    def test_claude_failure_leaves_domain_file_unchanged(self, tmp_path):
        corrections_text = """
## yelp — 2026-04-10
**Query:** Some query
**What was wrong:** Something
**Correct approach:** Fix
**Failure type:** UNKNOWN
"""
        corrections_file = self._make_corrections_file(tmp_path, corrections_text)
        domain_file = self._make_domain_file(tmp_path, "yelp")
        original_content = domain_file.read_text(encoding="utf-8")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API key invalid")

        with patch("utils.autodream.CORRECTIONS", corrections_file), \
             patch("utils.autodream.DOMAIN_DIR", tmp_path / "domain"), \
             patch("utils.autodream.get_client", return_value=mock_client), \
             patch("utils.autodream._update_changelog"):
            consolidate()

        # file should be unchanged because Claude failed and returned existing_content
        assert domain_file.read_text(encoding="utf-8") == original_content


# ── _update_changelog ─────────────────────────────────────────────────────────

class TestUpdateChangelog:
    def test_creates_changelog_if_missing(self, tmp_path):
        domain_dir = tmp_path / "domain"
        domain_dir.mkdir()
        changelog = domain_dir / "CHANGELOG.md"

        with patch("utils.autodream.DOMAIN_DIR", domain_dir):
            _update_changelog(["yelp", "bookreview"], 5)

        assert changelog.exists()
        content = changelog.read_text(encoding="utf-8")
        assert "autoDream run" in content
        assert "5" in content
        assert "yelp" in content

    def test_appends_to_existing_changelog(self, tmp_path):
        domain_dir = tmp_path / "domain"
        domain_dir.mkdir()
        changelog = domain_dir / "CHANGELOG.md"
        changelog.write_text("# Previous entry\n", encoding="utf-8")

        with patch("utils.autodream.DOMAIN_DIR", domain_dir):
            _update_changelog(["yelp"], 2)

        content = changelog.read_text(encoding="utf-8")
        assert "Previous entry" in content
        assert "autoDream run" in content
