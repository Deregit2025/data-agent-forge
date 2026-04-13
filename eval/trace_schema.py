"""
Trace Schema — Oracle Forge Evaluation Framework

Defines the data structures for evaluation results at three levels:
  TrialResult   — one agent run on one query
  QueryResult   — all trials for one query, with aggregated stats
  BenchmarkResult — the full benchmark run across all datasets/queries

All structures serialize to plain dicts for JSON storage.
"""

from dataclasses import dataclass, field
from typing import Optional


# ── trial (one agent run) ─────────────────────────────────────────────────────

@dataclass
class TrialResult:
    """Result of a single agent trial on one query."""
    dataset:      str
    query_id:     int
    trial_num:    int
    question:     str
    answer:       str
    is_valid:     bool
    reason:       str
    ground_truth: str
    elapsed_s:    float
    root_name:    str           = ""
    error:        Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "dataset":      self.dataset,
            "query_id":     self.query_id,
            "trial_num":    self.trial_num,
            "question":     self.question,
            "answer":       self.answer,
            "is_valid":     self.is_valid,
            "reason":       self.reason,
            "ground_truth": self.ground_truth,
            "elapsed_s":    self.elapsed_s,
            "root_name":    self.root_name,
            "error":        self.error,
        }


# ── query (aggregated across trials) ─────────────────────────────────────────

@dataclass
class QueryResult:
    """Aggregated results for one query across all trials."""
    dataset:      str
    query_id:     int
    question:     str
    ground_truth: str
    trials:       list = field(default_factory=list)   # list[TrialResult]

    # ── computed stats ──

    @property
    def n_trials(self) -> int:
        return len(self.trials)

    @property
    def pass_count(self) -> int:
        return sum(1 for t in self.trials if t.is_valid)

    @property
    def pass_rate(self) -> float:
        return round(self.pass_count / self.n_trials, 4) if self.n_trials else 0.0

    @property
    def majority_pass(self) -> bool:
        """True if more than half of trials passed — used as the query-level score."""
        return self.pass_count > self.n_trials / 2

    @property
    def any_pass(self) -> bool:
        """True if at least one trial passed."""
        return self.pass_count > 0

    @property
    def pass_at_1(self) -> bool:
        """True if the first trial passed."""
        return bool(self.trials) and self.trials[0].is_valid

    def to_dict(self) -> dict:
        return {
            "dataset":      self.dataset,
            "query_id":     self.query_id,
            "question":     self.question,
            "ground_truth": self.ground_truth,
            "n_trials":     self.n_trials,
            "pass_count":   self.pass_count,
            "pass_rate":    self.pass_rate,
            "majority_pass": self.majority_pass,
            "any_pass":     self.any_pass,
            "pass_at_1":    self.pass_at_1,
            "trials":       [t.to_dict() for t in self.trials],
        }


# ── dataset (aggregated across queries) ──────────────────────────────────────

@dataclass
class DatasetResult:
    """Aggregated results for one dataset."""
    dataset:        str
    n_queries:      int
    pass_count:     int    # queries with majority_pass=True
    any_pass_count: int    # queries where at least one trial passed
    pass_rate:      float  # pass_count / n_queries

    def to_dict(self) -> dict:
        return {
            "dataset":        self.dataset,
            "n_queries":      self.n_queries,
            "pass_count":     self.pass_count,
            "any_pass_count": self.any_pass_count,
            "pass_rate":      self.pass_rate,
        }


# ── benchmark (the full run) ──────────────────────────────────────────────────

@dataclass
class BenchmarkResult:
    """Full benchmark run result — all datasets and queries."""
    run_id:        str
    n_trials:      int
    model:         str
    total_queries: int
    pass_count:    int    # queries with majority_pass=True
    pass_rate:     float  # pass_count / total_queries
    per_dataset:   list = field(default_factory=list)   # list[DatasetResult]
    per_query:     list = field(default_factory=list)   # list[QueryResult]

    def to_dict(self) -> dict:
        return {
            "run_id":        self.run_id,
            "n_trials":      self.n_trials,
            "model":         self.model,
            "total_queries": self.total_queries,
            "pass_count":    self.pass_count,
            "pass_rate":     self.pass_rate,
            "per_dataset":   [d.to_dict() for d in self.per_dataset],
            "per_query":     [q.to_dict() for q in self.per_query],
        }
