import os
from pathlib import Path

# ── environment ───────────────────────────────────────────────────────────────

DAB_PATH = os.getenv(
    "DAB_PATH",
    "/home/project/oracle-forge/DataAgentBench"
)

# ── PostgreSQL ────────────────────────────────────────────────────────────────
# DB names match DAB db_config.yaml exactly

PG_CONFIG = {
    "host":     os.getenv("PG_HOST",     "127.0.0.1"),
    "port":     int(os.getenv("PG_PORT", "5432")),
    "user":     os.getenv("PG_USER",     "postgres"),
    "password": os.getenv("PG_PASSWORD", "postgres123"),
}

PG_TOOLS = {
    "query_postgres_bookreview": {
        "db":          "bookreview_db",
        "description": (
            "Query the bookreview PostgreSQL database. "
            "Contains books_info table with book details "
            "including title, author, genre, price and rating."
        ),
    },
    "query_postgres_crmarenapro": {
        "db":          "crm_support",
        "description": (
            "Query the crmarenapro support PostgreSQL database. "
            "Contains Case, casehistory__c, emailmessage, issue__c, "
            "knowledge__kav, livechattranscript tables."
        ),
    },
    "query_postgres_googlelocal": {
        "db":          "googlelocal_db",
        "description": (
            "Query the googlelocal PostgreSQL database. "
            "Contains business_description table with "
            "local business information."
        ),
    },
    "query_postgres_pancancer": {
        "db":          "pancancer_clinical",
        "description": (
            "Query the pancancer clinical PostgreSQL database. "
            "Contains clinical_info table with "
            "cancer patient clinical data."
        ),
    },
    "query_postgres_patents": {
        "db":          "patent_CPCDefinition",
        "description": (
            "Query the patents CPC definition PostgreSQL database. "
            "Contains cpc_definition table with "
            "patent classification definitions."
        ),
    },
}

# ── MongoDB ───────────────────────────────────────────────────────────────────
# DB names match DAB db_config.yaml exactly:
# articles_db → agnews dataset
# yelp_db     → yelp dataset

MONGO_CONFIG = {
    "uri": os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/"),
}

MONGO_TOOLS = {
    "query_mongo_yelp_business": {
        "database":    "yelp_db",
        "collection":  "business",
        "description": (
            "Query the yelp_db MongoDB database business collection. "
            "Contains business details including name, stars, "
            "categories, location and attributes."
        ),
    },
    "query_mongo_yelp_checkin": {
        "database":    "yelp_db",
        "collection":  "checkin",
        "description": (
            "Query the yelp_db MongoDB database checkin collection. "
            "Contains business checkin timestamps and frequency counts."
        ),
    },
    "query_mongo_agnews": {
        "database":    "articles_db",
        "collection":  "articles",
        "description": (
            "Query the articles_db MongoDB database articles collection. "
            "Contains news articles with title, description, "
            "category and source fields."
        ),
    },
}

# ── SQLite ────────────────────────────────────────────────────────────────────
# All paths confirmed against DAB db_config.yaml and file header check

SQLITE_TOOLS = {
    "query_sqlite_agnews_metadata": {
        "path":        Path(DAB_PATH) / "query_agnews"          / "query_dataset" / "metadata.db",
        "description": (
            "Query agnews metadata SQLite database. "
            "Contains metadata about news article categories."
        ),
    },
    "query_sqlite_bookreview": {
        "path":        Path(DAB_PATH) / "query_bookreview"       / "query_dataset" / "review_query.db",
        "description": (
            "Query bookreview SQLite database. "
            "Contains book review data including "
            "ratings, text reviews and reviewer info."
        ),
    },
    "query_sqlite_crmarenapro_core": {
        "path":        Path(DAB_PATH) / "query_crmarenapro"      / "query_dataset" / "core_crm.db",
        "description": (
            "Query crmarenapro core CRM SQLite database. "
            "Contains core CRM records including "
            "contacts, accounts and activities."
        ),
    },
    "query_sqlite_crmarenapro_products": {
        "path":        Path(DAB_PATH) / "query_crmarenapro"      / "query_dataset" / "products_orders.db",
        "description": (
            "Query crmarenapro products and orders SQLite database. "
            "Contains product catalog and order records."
        ),
    },
    "query_sqlite_crmarenapro_territory": {
        "path":        Path(DAB_PATH) / "query_crmarenapro"      / "query_dataset" / "territory.db",
        "description": (
            "Query crmarenapro territory SQLite database. "
            "Contains sales territory and assignment data."
        ),
    },
    "query_sqlite_deps_dev_package": {
        "path":        Path(DAB_PATH) / "query_DEPS_DEV_V1"      / "query_dataset" / "package_query.db",
        "description": (
            "Query deps.dev package SQLite database. "
            "Contains software package dependency information."
        ),
    },
    "query_sqlite_github_metadata": {
        "path":        Path(DAB_PATH) / "query_GITHUB_REPOS"     / "query_dataset" / "repo_metadata.db",
        "description": (
            "Query GitHub repos metadata SQLite database. "
            "Contains repository metadata including stars, "
            "forks, language and description."
        ),
    },
    "query_sqlite_googlelocal_review": {
        "path":        Path(DAB_PATH) / "query_googlelocal"      / "query_dataset" / "review_query.db",
        "description": (
            "Query googlelocal review SQLite database. "
            "Contains user reviews for local businesses "
            "including rating and review text."
        ),
    },
    "query_sqlite_music_brainz": {
        "path":        Path(DAB_PATH) / "query_music_brainz_20k" / "query_dataset" / "tracks.db",
        "description": (
            "Query music brainz tracks SQLite database. "
            "Contains music track metadata including "
            "artist, album, duration and release date."
        ),
    },
    "query_sqlite_patents": {
        "path":        Path(DAB_PATH) / "query_PATENTS"          / "query_dataset" / "patent_publication.db",
        "description": (
            "Query patents publication SQLite database. "
            "Contains patent publication records including "
            "title, abstract, inventors and classifications."
        ),
    },
    "query_sqlite_stockindex_info": {
        "path":        Path(DAB_PATH) / "query_stockindex"       / "query_dataset" / "indexInfo_query.db",
        "description": (
            "Query stock index info SQLite database. "
            "Contains stock index definitions and "
            "component information."
        ),
    },
    "query_sqlite_stockmarket_info": {
        "path":        Path(DAB_PATH) / "query_stockmarket"      / "query_dataset" / "stockinfo_query.db",
        "description": (
            "Query stock market info SQLite database. "
            "Contains individual stock information "
            "including ticker, company name and sector."
        ),
    },
}

# ── DuckDB ────────────────────────────────────────────────────────────────────
# All paths confirmed against DAB db_config.yaml and file header check
# Note: some files use .db extension but are confirmed DuckDB format

DUCKDB_TOOLS = {
    "query_duckdb_crmarenapro_activities": {
        "path":        Path(DAB_PATH) / "query_crmarenapro"      / "query_dataset" / "activities.duckdb",
        "description": (
            "Query the crmarenapro activities DuckDB database. "
            "Contains sales activity records including calls, emails, "
            "meetings and their outcomes linked to CRM accounts."
        ),
    },
    "query_duckdb_crmarenapro_sales": {
        "path":        Path(DAB_PATH) / "query_crmarenapro"      / "query_dataset" / "sales_pipeline.duckdb",
        "description": (
            "Query the crmarenapro sales pipeline DuckDB database. "
            "Contains sales pipeline stages, deal values, "
            "probability scores and forecast data."
        ),
    },
    "query_duckdb_music_brainz_sales": {
        "path":        Path(DAB_PATH) / "query_music_brainz_20k" / "query_dataset" / "sales.duckdb",
        "description": (
            "Query the music brainz sales DuckDB database. "
            "Contains music sales data including track sales figures, "
            "revenue and platform distribution."
        ),
    },
    "query_duckdb_deps_dev_project": {
        "path":        Path(DAB_PATH) / "query_DEPS_DEV_V1"      / "query_dataset" / "project_query.db",
        "description": (
            "Query the deps.dev project DuckDB database. "
            "Contains software project dependency graph data "
            "including version relationships and licenses."
        ),
    },
    "query_duckdb_github_artifacts": {
        "path":        Path(DAB_PATH) / "query_GITHUB_REPOS"     / "query_dataset" / "repo_artifacts.db",
        "description": (
            "Query the GitHub repos artifacts DuckDB database. "
            "Contains repository build artifacts, releases "
            "and deployment records."
        ),
    },
    "query_duckdb_yelp_user": {
        "path":        Path(DAB_PATH) / "query_yelp"             / "query_dataset" / "yelp_user.db",
        "description": (
            "Query the yelp user DuckDB database. "
            "Contains yelp user profiles including review count, "
            "useful votes, funny votes, cool votes and elite status. "
            "Also contains review and tip tables."
        ),
    },
    "query_duckdb_pancancer_molecular": {
        "path":        Path(DAB_PATH) / "query_PANCANCER_ATLAS"  / "query_dataset" / "pancancer_molecular.db",
        "description": (
            "Query the pancancer molecular DuckDB database. "
            "Contains molecular profiling data for cancer samples "
            "including gene expression and mutation data."
        ),
    },
    "query_duckdb_stockmarket_trade": {
        "path":        Path(DAB_PATH) / "query_stockmarket"      / "query_dataset" / "stocktrade_query.db",
        "description": (
            "Query the stock market trade DuckDB database. "
            "Contains individual stock trading history "
            "including price, volume and timestamps."
        ),
    },
    "query_duckdb_stockindex_trade": {
        "path":        Path(DAB_PATH) / "query_stockindex"       / "query_dataset" / "indextrade_query.db",
        "description": (
            "Query the stock index trade DuckDB database. "
            "Contains stock index trading history "
            "including open, close, high and low prices."
        ),
    },
}

# ── combined tool registry ────────────────────────────────────────────────────

ALL_TOOLS = {
    **{k: {**v, "db_type": "postgres"} for k, v in PG_TOOLS.items()},
    **{k: {**v, "db_type": "mongodb"}  for k, v in MONGO_TOOLS.items()},
    **{k: {**v, "db_type": "sqlite"}   for k, v in SQLITE_TOOLS.items()},
    **{k: {**v, "db_type": "duckdb"}   for k, v in DUCKDB_TOOLS.items()},
}


def get_tool(tool_name: str) -> dict:
    """Return tool config or raise ValueError if not found."""
    tool = ALL_TOOLS.get(tool_name)
    if tool is None:
        raise ValueError(
            f"Unknown tool: '{tool_name}'. "
            f"Available: {list(ALL_TOOLS.keys())}"
        )
    return tool