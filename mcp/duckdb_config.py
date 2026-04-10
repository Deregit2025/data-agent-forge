import os
from pathlib import Path

DAB_PATH = os.getenv(
    "DAB_PATH",
    "/home/project/oracle-forge/DataAgentBench"
)

# Every DuckDB file across all 12 DAB datasets
# Key   = logical name the agent uses to identify the database
# Value = absolute path to the .duckdb file on the server

DUCKDB_DATABASES = {
    # .duckdb extension files
    "crmarenapro_activities": Path(DAB_PATH) / "query_crmarenapro"       / "query_dataset" / "activities.duckdb",
    "crmarenapro_sales":      Path(DAB_PATH) / "query_crmarenapro"       / "query_dataset" / "sales_pipeline.duckdb",
    "music_brainz_sales":     Path(DAB_PATH) / "query_music_brainz_20k"  / "query_dataset" / "sales.duckdb",

    # .db extension files that are actually DuckDB databases
    "deps_dev_project":       Path(DAB_PATH) / "query_DEPS_DEV_V1"       / "query_dataset" / "project_query.db",
    "github_artifacts":       Path(DAB_PATH) / "query_GITHUB_REPOS"      / "query_dataset" / "repo_artifacts.db",
    "yelp_user":              Path(DAB_PATH) / "query_yelp"              / "query_dataset" / "yelp_user.db",
    "pancancer_molecular":    Path(DAB_PATH) / "query_PANCANCER_ATLAS"   / "query_dataset" / "pancancer_molecular.db",
    "stockmarket_trade":      Path(DAB_PATH) / "query_stockmarket"       / "query_dataset" / "stocktrade_query.db",
    "stockindex_trade":       Path(DAB_PATH) / "query_stockindex"        / "query_dataset" / "indextrade_query.db",
}

# Tool definitions exposed to the agent
# Each entry maps to one DuckDB file
# The agent reads the description to decide which tool to call

DUCKDB_TOOLS = {
    "query_duckdb_crmarenapro_activities": {
        "db_key":      "crmarenapro_activities",
        "description": (
            "Query the crmarenapro activities DuckDB database. "
            "Contains sales activity records including calls, emails, "
            "meetings and their outcomes linked to CRM accounts."
        ),
    },
    "query_duckdb_crmarenapro_sales": {
        "db_key":      "crmarenapro_sales",
        "description": (
            "Query the crmarenapro sales pipeline DuckDB database. "
            "Contains sales pipeline stages, deal values, "
            "probability scores and forecast data."
        ),
    },
    "query_duckdb_music_brainz_sales": {
        "db_key":      "music_brainz_sales",
        "description": (
            "Query the music brainz sales DuckDB database. "
            "Contains music sales data including track sales figures, "
            "revenue and platform distribution."
        ),
    },
    "query_duckdb_deps_dev_project": {
        "db_key":      "deps_dev_project",
        "description": (
            "Query the deps.dev project DuckDB database. "
            "Contains software project dependency graph data "
            "including version relationships and licenses."
        ),
    },
    "query_duckdb_github_artifacts": {
        "db_key":      "github_artifacts",
        "description": (
            "Query the GitHub repos artifacts DuckDB database. "
            "Contains repository build artifacts, releases "
            "and deployment records."
        ),
    },
    "query_duckdb_yelp_user": {
        "db_key":      "yelp_user",
        "description": (
            "Query the yelp user DuckDB database. "
            "Contains yelp user profiles including review count, "
            "useful votes, funny votes, cool votes and elite status."
        ),
    },
    "query_duckdb_pancancer_molecular": {
        "db_key":      "pancancer_molecular",
        "description": (
            "Query the pancancer molecular DuckDB database. "
            "Contains molecular profiling data for cancer samples "
            "including gene expression and mutation data."
        ),
    },
    "query_duckdb_stockmarket_trade": {
        "db_key":      "stockmarket_trade",
        "description": (
            "Query the stock market trade DuckDB database. "
            "Contains individual stock trading history "
            "including price, volume and timestamps."
        ),
    },
    "query_duckdb_stockindex_trade": {
        "db_key":      "stockindex_trade",
        "description": (
            "Query the stock index trade DuckDB database. "
            "Contains stock index trading history "
            "including open, close, high and low prices."
        ),
    },
}


def get_db_path(db_key: str) -> Path:
    """Return the file path for a given DuckDB database key."""
    path = DUCKDB_DATABASES.get(db_key)
    if path is None:
        raise ValueError(f"Unknown DuckDB database key: '{db_key}'")
    if not path.exists():
        raise FileNotFoundError(
            f"DuckDB file not found at {path}. "
            f"Check DAB_PATH is set correctly: {DAB_PATH}"
        )
    return path


def list_databases() -> dict:
    """Return all registered DuckDB databases with their existence status."""
    return {
        key: {
            "path":   str(path),
            "exists": path.exists(),
        }
        for key, path in DUCKDB_DATABASES.items()
    }