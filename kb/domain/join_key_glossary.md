# Join Key Glossary — All Datasets

Complete reference for cross-database join keys. Supplements Section 4 of AGENT.md.

---

## yelp
| Left table | Left field | Left format | Right table | Right field | Right format | Rule |
|---|---|---|---|---|---|---|
| MongoDB `business` | `business_id` | `businessid_##` | DuckDB `review` | `business_ref` | `businessref_##` | Replace prefix `businessid_` → `businessref_` |
| MongoDB `business` | `business_id` | `businessid_##` | DuckDB `tip` | `business_ref` | `businessref_##` | Same prefix replacement |
| DuckDB `review` | `user_id` | plain string | DuckDB `user` | `user_id` | plain string | Direct match |
| DuckDB `tip` | `user_id` | plain string | DuckDB `user` | `user_id` | plain string | Direct match |
| MongoDB `checkin` | `business_id` | `businessid_##` | MongoDB `business` | `business_id` | `businessid_##` | Direct match |

---

## bookreview
| Left table | Left field | Right table | Right field | Rule |
|---|---|---|---|---|
| PostgreSQL `books_info` | `book_id` | SQLite `review` | `purchase_id` | May require prefix substitution — verify format before joining |

---

## googlelocal
| Left table | Left field | Right table | Right field | Rule |
|---|---|---|---|---|
| PostgreSQL `business_description` | `gmap_id` | SQLite `review` | `gmap_id` | Direct string match |

**WARNING:** `business_description.state` = operating status ("Open", "Temporarily closed") — NOT a US state.

---

## agnews
| Left table | Left field | Right table | Right field | Rule |
|---|---|---|---|---|
| MongoDB `articles` | `article_id` | SQLite `article_metadata` | `article_id` | Direct integer match |
| SQLite `article_metadata` | `author_id` | SQLite `authors` | `author_id` | Direct integer match |

---

## crmarenapro
| Left table | Left field | Right table | Right field | Rule |
|---|---|---|---|---|
| PostgreSQL `Case` | `id` | DuckDB `Event` | `WhatId` | Direct string match |
| PostgreSQL `Case` | `accountid` | SQLite `Account` | `Id` | Direct string match |
| DuckDB `Opportunity` | `AccountId` | SQLite `Account` | `Id` | Direct string match |
| DuckDB `Opportunity` | `OwnerId` | SQLite `User` | `Id` | Direct string match |
| SQLite `Order` | `AccountId` | SQLite `Account` | `Id` | Direct string match |
| SQLite `OrderItem` | `Product2Id` | SQLite `Product2` | `Id` | Direct string match |
| DuckDB `Quote` | `OpportunityId` | DuckDB `Opportunity` | `Id` | Direct string match |

---

## music_brainz
| Left table | Left field | Right table | Right field | Rule |
|---|---|---|---|---|
| SQLite `tracks` | `track_id` | DuckDB `sales` | `track_id` | Direct integer match |

---

## deps_dev
| Left table | Left field | Right table | Right field | Rule |
|---|---|---|---|---|
| SQLite `packageinfo` | `Name` + `Version` | DuckDB `project_packageversion` | `Name` + `Version` | Composite match on both fields |

---

## github_repos
| Left table | Left field | Right table | Right field | Rule |
|---|---|---|---|---|
| SQLite `repos` | `repo_name` | DuckDB `commits` | `repo_name` | Direct string match (`owner/repo` format) |
| SQLite `repos` | `repo_name` | DuckDB `contents` | `sample_repo_name` | Direct string match |
| SQLite `licenses` | `repo_name` | SQLite `repos` | `repo_name` | Direct string match |
| SQLite `languages` | `repo_name` | SQLite `repos` | `repo_name` | Direct string match |

---

## pancancer
| Left table | Left field | Right table | Right field | Rule |
|---|---|---|---|---|
| PostgreSQL `clinical_info` | `ParticipantBarcode` | SQLite `Mutation_Data` | `ParticipantBarcode` | Direct string match |
| PostgreSQL `clinical_info` | `ParticipantBarcode` | SQLite `RNASeq_Expression` | `ParticipantBarcode` | Direct string match |

---

## patents
| Left table | Left field | Right table | Right field | Rule |
|---|---|---|---|---|
| SQLite `publicationinfo` | `cpc` (JSON-like field) | PostgreSQL `cpc_definition` | `symbol` | Parse CPC codes from JSON, match to symbol |

---

## stockindex
| Left table | Left field | Right table | Right field | Rule |
|---|---|---|---|---|
| SQLite `index_info` | `Exchange` (full name) | DuckDB `index_trade` | `Index` (abbreviation) | No direct key — use known abbreviation mapping |

---

## stockmarket
No cross-database join key needed. Each DuckDB table IS the ticker symbol.
Use SQLite `stockinfo.Symbol` to find the ticker, then query `SELECT * FROM {Symbol}` in DuckDB directly.
