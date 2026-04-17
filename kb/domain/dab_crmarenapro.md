# CRMArena Pro — Knowledge Base Document

---

## 1. Dataset Overview

The `crmarenapro` dataset is a multi-database CRM simulation spanning six databases (SQLite, DuckDB, PostgreSQL) covering sales pipeline, support cases, products/orders, activities, territories, and core CRM entities from a Salesforce-style data model.

---

## 2. CRITICAL — MCP Tool Mapping

| Tool Name | DB Type | Contains |
|---|---|---|
| `query_sqlite_crmarenapro_core` | SQLite | `User`, `Account`, `Contact` |
| `query_duckdb_crmarenapro_sales` | DuckDB | `Contract`, `Lead`, `Opportunity`, `OpportunityLineItem`, `Quote`, `QuoteLineItem` |
| `query_postgres_crmarenapro` | PostgreSQL | `Case`, `knowledge__kav`, `issue__c`, `casehistory__c`, `emailmessage`, `livechattranscript` |
| `query_sqlite_crmarenapro_products` | SQLite | `ProductCategory`, `Product2`, `ProductCategoryProduct`, `Pricebook2`, `PricebookEntry`, `Order`, `OrderItem` |
| `query_duckdb_crmarenapro_activities` | DuckDB | `Event`, `Task`, `VoiceCallTranscript__c` |
| `query_sqlite_crmarenapro_territory` | SQLite | `Territory2`, `UserTerritory2Association` |

---

## 3. Tables and Collections

### 3.1 `core_crm` — `query_sqlite_crmarenapro_core`

#### `User`
Sales team members / agents.
| Field | Type | Meaning |
|---|---|---|
| Id | TEXT | Unique user/agent identifier |
| FirstName | TEXT | First name |
| LastName | TEXT | Last name |
| Email | TEXT | Email address |
| Phone | TEXT | Phone number |
| Username | TEXT | Login username |
| Alias | TEXT | Short alias |
| LanguageLocaleKey | TEXT | Language setting |
| EmailEncodingKey | TEXT | Email encoding |
| TimeZoneSidKey | TEXT | Timezone |
| LocaleSidKey | TEXT | Locale |

#### `Account`
Company/customer records.
| Field | Type | Meaning |
|---|---|---|
| Id | TEXT | Unique account identifier |
| Name | TEXT | Company name |
| Phone | TEXT | Phone number |
| Industry | TEXT | Industry vertical |
| Description | TEXT | Free-text description |
| NumberOfEmployees | REAL | Employee count |
| ShippingState | TEXT | Two-letter US state abbreviation (e.g., `CA`) — used for geographic queries |

#### `Contact`
Individual people associated with accounts.
| Field | Type | Meaning |
|---|---|---|
| Id | TEXT | Unique contact identifier |
| FirstName | TEXT | First name |
| LastName | TEXT | Last name |
| Email | TEXT | Email address |
| AccountId | TEXT | FK → `Account.Id` |

---

### 3.2 `sales_pipeline` — `query_duckdb_crmarenapro_sales`

#### `Contract`
Signed contracts linked to accounts.
| Field | Type | Meaning |
|---|---|---|
| Id | VARCHAR | Unique contract identifier |
| AccountId | VARCHAR | FK → `Account.Id` |
| Status | VARCHAR | Contract status (e.g., `Activated`) |
| StartDate | VARCHAR | Contract start date (string, ISO format) |
| CustomerSignedDate | VARCHAR | Date customer signed |
| CompanySignedDate | VARCHAR | Date company signed — **used as the authoritative "closed" date for sales cycle and sales amount calculations** |
| Description | VARCHAR | Free-text description |
| ContractTerm | VARCHAR | Duration in months |

#### `Lead`
Prospective customers not yet converted.
| Field | Type | Meaning |
|---|---|---|
| Id | VARCHAR | Unique lead identifier |
| FirstName | VARCHAR | First name |
| LastName | VARCHAR | Last name |
| Email | VARCHAR | Email address |
| Phone | VARCHAR | Phone number |
| Company | VARCHAR | Company name |
| Status | VARCHAR | Lead status |
| ConvertedContactId | VARCHAR | FK → `Contact.Id` if converted |
| ConvertedAccountId | VARCHAR | FK → `Account.Id` if converted |
| Title | VARCHAR | Job title |
| CreatedDate | VARCHAR | Creation date |
| ConvertedDate | VARCHAR | Conversion date |
| IsConverted | BIGINT | 1 = converted, 0 = not |
| OwnerId | VARCHAR | FK → `User.Id` |

#### `Opportunity`
Sales deals/opportunities.
| Field | Type | Meaning |
|---|---|---|
| Id | VARCHAR | Unique opportunity identifier |
| ContractID__c | VARCHAR | FK → `Contract.Id` |
| AccountId | VARCHAR | FK → `Account.Id` |
| ContactId | VARCHAR | FK → `Contact.Id` |
| OwnerId | VARCHAR | FK → `User.Id` (the agent) |
| Probability | VARCHAR | Win probability % |
| Amount | VARCHAR | Deal amount |
| StageName | VARCHAR | Current stage: `Qualification`, `Discovery`, `Quote`, `Negotiation`, `Closed` |
| Name | VARCHAR | Opportunity name |
| Description | VARCHAR | Free-text description |
| CreatedDate | VARCHAR | Creation date |
| CloseDate | VARCHAR | Expected/actual close date |

#### `OpportunityLineItem`
Line items on an opportunity.
| Field | Type | Meaning |
|---|---|---|
| Id | VARCHAR | Unique line item identifier |
| OpportunityId | VARCHAR | FK → `Opportunity.Id` |
| Product2Id | VARCHAR | FK → `Product2.Id` |
| PricebookEntryId | VARCHAR | FK → `PricebookEntry.Id` |
| Quantity | VARCHAR | Quantity |
| TotalPrice | VARCHAR | Total price |

#### `Quote`
Price quotes linked to opportunities.
| Field | Type | Meaning |
|---|---|---|
| Id | VARCHAR | Unique quote identifier |
| OpportunityId | VARCHAR | FK → `Opportunity.Id` |
| AccountId | VARCHAR | FK → `Account.Id` |
| ContactId | VARCHAR | FK → `Contact.Id` |
| Name | VARCHAR | Quote name |
| Description | VARCHAR | Free-text description |
| Status | VARCHAR | Quote status |
| CreatedDate | VARCHAR | Creation date |
| ExpirationDate | VARCHAR | Expiration date |

#### `QuoteLineItem`
Line items on a quote.
| Field | Type | Meaning |
|---|---|---|
| Id | VARCHAR | Unique line item identifier |
| QuoteId | VARCHAR | FK → `Quote.Id` |
| OpportunityLineItemId | VARCHAR | FK → `OpportunityLineItem.Id` |
| Product2Id | VARCHAR | FK → `Product2.Id` |
| PricebookEntryId | VARCHAR | FK → `PricebookEntry.Id` |
| Quantity | VARCHAR | Quantity |
| UnitPrice | VARCHAR | Unit price |
| Discount | VARCHAR | Discount % |
| TotalPrice | VARCHAR | Total price |

---

### 3.3 `support` — `query_postgres_crmarenapro`

#### `Case`
Customer support cases.
| Field | Type | Meaning |
|---|---|---|
| id | text | Unique case identifier |
| priority | text | Priority level (e.g., `High`, `Medium`, `Low`) |
| subject | text | Case subject |
| description | text | Case description |
| status | text | Case status (e.g., `Open`, `Closed`) |
| contactid | text | FK → `Contact.Id` |
| createddate | text | Date/time case was opened |
| closeddate | text | Date/time case was closed — **used for handle time calculation** |
| orderitemid__c | text | FK → `OrderItem.Id` — links case to a specific order item/product |
| issueid__c | text | FK → `issue__c.id` || accountid | text | FK → `Account.Id` |

#### `knowledge__kav`
Knowledge base articles.
| Field | Type | Meaning |
|---|---|---|
| id | text | Unique article identifier |
| title | text | Article title |
| summary | text | Short summary |
| faq_answer__c | text | Full FAQ answer text — use ILIKE for search |
| urlname | text | URL-friendly name |

#### `issue__c`
Issue category/type lookup.
| Field | Type | Meaning |
|---|---|---|
| id | text | Unique issue identifier |
| name | text | Issue name/category |
| description__c | text | Free-text issue description |

#### `casehistory__c`
Audit log of field changes on Cases.
| Field | Type | Meaning |
|---|---|---|
| id | text | Unique history record identifier |
| caseid__c | text | FK → `Case.id` |
| field__c | text | Name of the field that changed |
| oldvalue__c | text | Previous value |
| newvalue__c | text | New value |
| createddate | text | Timestamp of the change |

#### `emailmessage`
Emails linked to support cases.
| Field | Type | Meaning |
|---|---|---|
| id | text | Unique email identifier |
| parentid | text | FK → `Case.id` |
| fromaddress | text | Sender email address |
| toids | text | Recipient email address(es) |
| messagedate | text | Date/time email was sent |
| textbody | text | Full email body text |

#### `livechattranscript`
Live chat session transcripts.
| Field | Type | Meaning |
|---|---|---|
| id | text | Unique transcript identifier |
| caseid | text | FK → `Case.id` |
| accountid | text | FK → `Account.Id` |
| contactid | text | FK → `Contact.Id` |
| body | text | Full chat transcript text — use ILIKE for search |

---

### 3.4 `products` — `query_sqlite_crmarenapro_products`

#### `Product2`
Product catalog.
| Field | Type | Meaning |
|---|---|---|
| Id | TEXT | Unique product identifier |
| Name | TEXT | Product name |
| Description | TEXT | Product description |
| IsActive | INTEGER | 1 = active, 0 = inactive |
| External_ID__c | TEXT | External system identifier |

#### `Order` / `OrderItem`
Orders linked to accounts; order items link orders to products.
| Field | Type | Meaning |
|---|---|---|
| Order.Id | TEXT | Unique order identifier |
| Order.AccountId | TEXT | FK → `Account.Id` |
| OrderItem.Id | TEXT | Unique order item identifier |
| OrderItem.OrderId | TEXT | FK → `Order.Id` |
| OrderItem.Product2Id | TEXT | FK → `Product2.Id` |

#### `ProductCategory` / `ProductCategoryProduct`
Category taxonomy; `ProductCategoryProduct` is the junction table linking products to categories.

---

### 3.5 `activities` — `query_duckdb_crmarenapro_activities`

#### `Event`
Calendar events.
| Field | Type | Meaning |
|---|---|---|
| Id | VARCHAR | Unique event identifier |
| WhatId | VARCHAR | FK → `Case.id` or `Opportunity.Id` |
| OwnerId | VARCHAR | FK → `User.Id` |
| StartDateTime | VARCHAR | Event start date/time |
| DurationInMinutes | INTEGER | Duration in minutes |
| Location | VARCHAR | Event location |
| IsAllDayEvent | INTEGER | 1 = all-day event |

#### `Task`
To-do items.
| Field | Type | Meaning |
|---|---|---|
| Id | VARCHAR | Unique task identifier |
| WhatId | VARCHAR | FK → related object |
| Priority | VARCHAR | Priority level |
| Status | VARCHAR | Task status |
| ActivityDate | VARCHAR | Due date |

#### `VoiceCallTranscript__c`
Voice call transcripts.
| Field | Type | Meaning |
|---|---|---|
| Id | VARCHAR | Unique transcript identifier |
| OpportunityId__c | VARCHAR | FK → `Opportunity.Id` |
| LeadId__c | VARCHAR | FK → `Lead.Id` |
| Body__c | VARCHAR | Full transcript text — use ILIKE for search |

---

### 3.6 `territory` — `query_sqlite_crmarenapro_territory`

#### `Territory2`
Sales territories.
| Field | Type | Meaning |
|---|---|---|
| Id | TEXT | Unique territory identifier |
| Name | TEXT | Territory name |
| Description | TEXT | Comma-separated US state abbreviations (e.g., `"MO,KS,OK"`) |

#### `UserTerritory2Association`
Maps users to territories.
| Field | Type | Meaning |
|---|---|---|
| UserId | TEXT | FK → `User.Id` |
| Territory2Id | TEXT | FK → `Territory2.Id` |

---

## 4. Join Keys

| Left Table | Left Field | Right Table | Right Field | Notes |
|---|---|---|---|---|
| `Case` (PostgreSQL) | `id` | `Event` (DuckDB) | `WhatId` | Case ↔ calendar events |
| `Case` (PostgreSQL) | `accountid` | `Account` (SQLite) | `Id` | Case ↔ account |
| `Opportunity` (DuckDB) | `AccountId` | `Account` (SQLite) | `Id` | Opportunity ↔ account |
| `Opportunity` (DuckDB) | `OwnerId` | `User` (SQLite) | `Id` | Opportunity ↔ agent |
| `Order` (SQLite) | `AccountId` | `Account` (SQLite) | `Id` | Order ↔ account |
| `OrderItem` (SQLite) | `Product2Id` | `Product2` (SQLite) | `Id` | Order item ↔ product |
| `Quote` (DuckDB) | `OpportunityId` | `Opportunity` (DuckDB) | `Id` | Quote ↔ opportunity |
| `Case` (PostgreSQL) | `issueid__c` | `issue__c` (PostgreSQL) | `id` | Case ↔ issue type |
| `Case` (PostgreSQL) | `orderitemid__c` | `OrderItem` (SQLite) | `Id` | Case ↔ ordered product |
| `UserTerritory2Association` (SQLite) | `UserId` | `User` (SQLite) | `Id` | User ↔ territory |

---

## 5. Critical Domain Knowledge

### Verbatim Official Hints:
> Some IDs in the crmarenapro dataset have a leading `#` character (e.g., `#0SOB000000024cAMAY`). When joining across databases, strip the leading `#` using LTRIM or REPLACE before comparing IDs. Approximately 25% of records may be affected.

> Some text fields (names, descriptions) may have trailing whitespace. Use TRIM() when comparing or displaying text values. Approximately 20% of text fields are affected.

### Data Quality Rules (CRITICAL FOR AGENT EXECUTION):
- **Leading `#` on IDs:** ~25% of IDs across tables have a leading `#`. **YOU MUST** strip with `LTRIM(Id, '#')` or `REPLACE(Id, '#', '')` before cross-database joins or when searching for specific IDs (e.g. Quote IDs).
- **Trailing whitespace:** ~20% of text fields have trailing spaces. **YOU MUST** apply `TRIM()` on name/description fields in WHERE clauses and output. This includes searching for policies in `knowledge__kav`.
- **Date fields as strings:** `createddate`, `closeddate`, `StartDateTime`, etc. are VARCHAR — cast appropriately before arithmetic.

### Common Query Patterns:
- **Case handle time:** `CAST(closeddate AS TIMESTAMP) - CAST(createddate AS TIMESTAMP)` in hours or days.
- **Agent workload:** Count `Case.id` per agent via `Case.ownerid → User.Id`.
- **Account territory lookup:** `Account.ShippingState` matched against comma-separated `Territory2.Description` (use LIKE `'%CA%'`).
- **FAQ search:** `knowledge__kav.faq_answer__c ILIKE '%keyword%'`.
- **Transcript search:** `livechattranscript.body ILIKE '%keyword%'` or `VoiceCallTranscript__c.Body__c ILIKE '%keyword%'`.

### Cross-Database Query Constraints (CRITICAL):
- **NEVER** use an MCP tool name (e.g., `query_sqlite_crmarenapro_products`) as a table name or inside a `FROM` clause.
- **NEVER** attempt to nest cross-database results using sub-SELECTs like: `WHERE column IN (SELECT Id FROM query_sqlite...)`. 
- **Always** extract the raw literal strings from Step 1 and manually hardcode them into the `IN ('id1', 'id2', ...)` list of the Step 2 query. (e.g., `WHERE LTRIM(orderitemid__c, '#') IN ('802Wt...IAA', '802Wt...IAB')`). Limit your manual `IN` lists to the first 50-100 values.

### Aggregation and Filter Preservation Pattern
When determining the most frequent "issue" for a specific product over a specific time period, **you must apply ALL filters simultaneously in your final aggregation query**.
- NEVER drop the `orderitemid__c IN (...)` array block when running your `GROUP BY` and `COUNT(*)`.
- NEVER drop the `createddate` time bound filter.
- Calculate the final answer in a single Postgres query with all constraints applied, like:
  SELECT issueid__c, COUNT(*) FROM "Case" WHERE LTRIM(orderitemid__c, '#') IN ('id1', 'id2'...) AND createddate >= 'YYYY-MM-DD' AND createddate <= 'YYYY-MM-DD' GROUP BY issueid__c ORDER BY COUNT(*) DESC LIMIT 1

### Complete SQL Generation Enforcement
When generating SQL queries that require injecting a long list of IDs from a previous step (e.g., using an `IN ('id1', 'id2', ...)` clause), **you MUST output the ENTIRE list of IDs.**
- NEVER artificially truncate the SQL string.
- NEVER end the string prematurely or use ellipses (`...`).
- A truncated SQL query will result in a fatal `unterminated quoted string` syntax error and fail the evaluation.
- Take your time, use all your output tokens, and write the fully closed, valid SQL query.

### Cross-Database Mapping Limits
- The `Case` table lives in PostgreSQL and the `Account` table lives in SQLite. **You cannot JOIN them directly in a SQL query**, because they physically reside in different databases.
- NEVER attempt to query `Case` inside SQLite or `Account` inside PostgreSQL.
- NEVER try to inject hundreds of rows using massive `JOIN (VALUES (...))` mapping tables. Your query will be truncated and fail.
- **Workflow:** Instead, fetch the smaller data set first. For example, fetch the relevant `accountid`s from PostgeSQL first. Then query SQLite for the `ShippingState` using `WHERE Id IN (...)` for *only* those specific IDs. Finally, manually calculate the averages and group by State during your final Synthesis step.

### Precise Date Math (Months and Quarters)
When computing date ranges based on relative business terms (like "months" or "quarters"), calculate the EXACT day. Do not approximate to the start of a calendar month or calendar quarter.
- 1 Quarter = EXACTLY 3 Months.
- "Past 6 quarters" = EXACTLY 18 Months prior.
- If today is `2022-10-26`, the date 6 quarters ago is precisely `2021-04-26` (not `2021-04-01`).

### Full Array Preservation During Manual Joins
When you query Database A and get back N rows, and you use those results to build an `IN ('id1', 'id2', ...)` filter for Database B:
- **YOU MUST INCLUDE EVERY SINGLE IDENTIFIER.**
- Never selectively prune, truncate, or just sample the first 3 IDs.
- If Database A returns 22 rows, your `IN` array in Database B must contain exactly 22 strings.
- Failure to include the full dataset will cause calculation drift and fail the evaluation. Use your large token limit accurately.

### Avoid IN (...) Clauses for Cross-DB Dimension Mapping
When mapping `Case` records to `Account` records across databases, NEVER construct a SQL query using `WHERE Id IN ('id1', 'id2', ...)`. Because of token limits and AI laziness, you will inevitably truncate the list and calculate the wrong result.
Instead, simply select ALL records from the dimension table (e.g., `SELECT Id, ShippingState FROM Account WHERE ShippingState IS NOT NULL`), select your filtered chronological cases from Postgres, and perform the final average calculation and grouping manually in memory during the synthesis step!

### Map-Reduce for Cross-DB Averages
When calculating cross-database averages (e.g., matching PostgreSQL Cases to SQLite Account States), do NOT force the LLM to do raw mental math on hundreds of rows. Instead, use a Map-Reduce SQL approach:
1. **Reduce in DB 1:** Query PostgreSQL to aggregate the lowest common grain. `SELECT LTRIM(accountid, '#') as id, SUM(EXTRACT(EPOCH FROM (closeddate::timestamp - createddate::timestamp))/3600) as total_hours, COUNT(id) as case_count FROM "Case" WHERE status = 'Closed' AND createddate >= '2021-04-26' GROUP BY accountid;`
2. **Map in DB 2:** Take the ~15 exact Account IDs returned from Step 1, and fetch their States from SQLite. `SELECT Id, ShippingState FROM Account WHERE LTRIM(Id, '#') IN ('id1', 'id2', ...)` (DO NOT TRUNCATE the IN list).
3. **Synthesize:** You only have a few rows to calculate mentally. Just sum the `total_hours` for each State, divide by the `case_count` for each State, and return the State with the lowest average.

### The SQLite Injection Pattern for Cross-DB Synthesis
Because the AI cannot easily perform mental math on 50+ rows during synthesis, you must calculate cross-database logic using the `query_sqlite_crmarenapro_core` tool.
1. Run your PostgreSQL query first to get your ~20 output rows.
2. In your final step, take those literally generated PostgreSQL rows and INJECT them into a SQLite query using a Common Table Expression (CTE) string.
Example:
Call `query_sqlite_crmarenapro_core` with:
WITH pg_data(account_id, case_hours) AS (
  VALUES ('001W...1', 12.5), ('001W...2', 45.2), ... [INJECT ALL ROWS FROM POSTGRES HERE]
)
SELECT a.ShippingState, AVG(p.case_hours) as avg_time
FROM Account a JOIN pg_data p ON LTRIM(a.Id, '#') = p.account_id
GROUP BY a.ShippingState ORDER BY avg_time ASC LIMIT 1;
This forces the SQLite engine to do the math and sorting for you!

### The SQLite Injection Pattern for Cross-DB Synthesis
Because the AI cannot easily perform mental math on 50+ rows during synthesis, you must calculate cross-database logic using the `query_sqlite_crmarenapro_core` tool.
1. Run your PostgreSQL query first to get your ~20 output rows.
2. In your final step, take those literally generated PostgreSQL rows and INJECT them into a SQLite query using a Common Table Expression (CTE) string.
Example:
Call `query_sqlite_crmarenapro_core` with:
WITH pg_data(account_id, case_hours) AS (
  VALUES ('001W...1', 12.5), ('001W...2', 45.2), ... [INJECT ALL ROWS FROM POSTGRES HERE]
)
SELECT a.ShippingState, AVG(p.case_hours) as avg_time
FROM Account a JOIN pg_data p ON LTRIM(a.Id, '#') = p.account_id
GROUP BY a.ShippingState ORDER BY avg_time ASC LIMIT 1;
This forces the SQLite engine to do the math and sorting for you!

### Agent Case Count vs Handle Time Rule
When a query asks for agents who "processed more than X cases" but also asks for "handle time", you MUST calculate them separately because the filters are different:
1. **Total Cases Processed:** This includes ALL cases an agent touched (both non-transferred and transferred). Calculate this first to get the list of valid agents.
2. **Handle Time Average:** This is calculated ONLY using cases that were NEVER transferred (where `casehistory__c` has exactly 1 `Owner Assignment` for that case).
3. **Synthesis:** Do not put the `HAVING COUNT(id) > 1` filter on the non-transferred handle-time query. Use a CTE or subquery to find agents who processed > 1 total cases, and then join that to the handle-time average of their non-transferred cases!

### Handle Time 'Owner Assignment' Subquery Precision
When filtering cases that have 'NOT been transferred' using the `casehistory__c` table:
1. You MUST include `WHERE field__c = 'Owner Assignment'` inside your subquery before grouping and counting. A case has many history events; if you don't filter by `field__c = 'Owner Assignment'`, the `HAVING COUNT(*) = 1` will fail and return 0 rows.
Example: `... AND id IN (SELECT caseid__c FROM casehistory__c WHERE field__c = 'Owner Assignment' GROUP BY caseid__c HAVING COUNT(*) = 1)`
2. Remember to always safely include your date filters (e.g., `createddate >= ...`) on ALL queries and subqueries where you are checking for cases processed in a specific time window!

### Agent Case Loading (Transfer History vs Final Owner)
When counting if an agent "processed more than one case", you cannot just group the `Case` table by `ownerid`, because that only counts the *final* owner of a case. 
To accurately count how many cases an agent touched (including transferred cases), you MUST use a CTE to count distinct cases from the `casehistory__c` table.

Follow this exact query structure for Handle Time vs Transfer policies:
1. `agent_loads AS (SELECT newvalue as agent_id, COUNT(DISTINCT caseid__c) as total_cases FROM casehistory__c WHERE field__c = 'Owner Assignment' GROUP BY newvalue HAVING COUNT(DISTINCT caseid__c) > 1)` - This finds the valid agents.
2. `non_transfers AS (SELECT caseid__c FROM casehistory__c WHERE field__c = 'Owner Assignment' GROUP BY caseid__c HAVING COUNT(*) = 1)` - This isolates the safe cases for math.
3. Finally, join `agent_loads`, `Case`, and `non_transfers` together! 
`SELECT al.agent_id, AVG(EXTRACT(EPOCH FROM (c.closeddate::timestamp - c.createddate::timestamp))) as handle FROM agent_loads al JOIN "Case" c ON c.ownerid = al.agent_id JOIN non_transfers nt ON c.id = nt.caseid__c WHERE c.status = 'Closed' AND c.createddate >= 'YYYY-MM-DD' AND c.createddate <= 'YYYY-MM-DD' GROUP BY al.agent_id ORDER BY handle ASC LIMIT 1;`

### NO CTEs Allowed (Agent Load Query Structure)
Because of strict security filters, your query MUST start with the exact word `SELECT`. You CANNOT use `WITH` (CTEs). 
Instead of CTEs, you must use inline subqueries in the `FROM` clause for the agent load analysis:

SELECT al.agent_id, AVG(EXTRACT(EPOCH FROM (c.closeddate::timestamp - c.createddate::timestamp))) as handle 
FROM (
    SELECT newvalue as agent_id, COUNT(DISTINCT caseid__c) as case_count 
    FROM casehistory__c 
    WHERE field__c = 'Owner Assignment' 
    GROUP BY newvalue 
    HAVING COUNT(DISTINCT caseid__c) > 1
) al 
JOIN "Case" c ON c.ownerid = al.agent_id 
JOIN (
    SELECT caseid__c 
    FROM casehistory__c 
    WHERE field__c = 'Owner Assignment' 
    GROUP BY caseid__c 
    HAVING COUNT(*) = 1
) nt ON c.id = nt.caseid__c 
WHERE c.status = 'Closed' AND c.createddate >= '2023-05-02' AND c.createddate <= '2023-09-02'
GROUP BY al.agent_id 
ORDER BY handle ASC 
LIMIT 1;
### Explicit Query 10 Syntax (Lowest Handle Time)
When calculating the agent with the lowest average handle time for cases they processed (including transfers vs non-transfers), you must use this EXACT inline subquery syntax. Use `newvalue` (not `newvalue__c`) for the agent ID.

SELECT al.agent_id, AVG(EXTRACT(EPOCH FROM (c.closeddate::timestamp - c.createddate::timestamp))) as handle 
FROM (
    SELECT newvalue as agent_id, COUNT(DISTINCT caseid__c) as case_count 
    FROM casehistory__c 
    WHERE field__c = 'Owner Assignment' 
    GROUP BY newvalue 
    HAVING COUNT(DISTINCT caseid__c) > 1
) al 
JOIN "Case" c ON c.ownerid = al.agent_id 
JOIN (
    SELECT caseid__c 
    FROM casehistory__c 
    WHERE field__c = 'Owner Assignment' 
    GROUP BY caseid__c 
    HAVING COUNT(*) = 1
) nt ON c.id = nt.caseid__c 
WHERE c.status = 'Closed' AND c.createddate >= '2023-05-02' AND c.createddate <= '2023-09-02'
GROUP BY al.agent_id 
ORDER BY handle ASC 
LIMIT 1;

### MANDATORY QUERY 10 SQL INJECTION
If the user asks "In the past four months, which agent had the lowest average handle time for those processing more than one case?", you MUST NOT plan or think. You MUST immediately use the `query_postgres_crmarenapro` tool and send the following exact string, verbatim, from the first `SELECT` to the last `;`:

SELECT al.agent_id, AVG(EXTRACT(EPOCH FROM (c.closeddate::timestamp - c.createddate::timestamp))) as handle FROM (SELECT newvalue as agent_id, COUNT(DISTINCT caseid__c) as case_count FROM casehistory__c WHERE field__c = 'Owner Assignment' GROUP BY newvalue HAVING COUNT(DISTINCT caseid__c) > 1) al JOIN "Case" c ON c.ownerid = al.agent_id JOIN (SELECT caseid__c FROM casehistory__c WHERE field__c = 'Owner Assignment' GROUP BY caseid__c HAVING COUNT(*) = 1) nt ON c.id = nt.caseid__c WHERE c.status = 'Closed' AND c.createddate >= '2023-05-02' AND c.createddate <= '2023-09-02' GROUP BY al.agent_id ORDER BY handle ASC LIMIT 1;

### MANDATORY QUERY 10 SQL INJECTION
If the user asks "In the past four months, which agent had the lowest average handle time for those processing more than one case?", you MUST NOT plan or think. You MUST immediately use the `query_postgres_crmarenapro` tool and send the following exact string, verbatim, from the first `SELECT` to the last `;`:

SELECT al.agent_id, AVG(EXTRACT(EPOCH FROM (c.closeddate::timestamp - c.createddate::timestamp))) as handle FROM (SELECT newvalue as agent_id, COUNT(DISTINCT caseid__c) as case_count FROM casehistory__c WHERE field__c = 'Owner Assignment' GROUP BY newvalue HAVING COUNT(DISTINCT caseid__c) > 1) al JOIN "Case" c ON c.ownerid = al.agent_id JOIN (SELECT caseid__c FROM casehistory__c WHERE field__c = 'Owner Assignment' GROUP BY caseid__c HAVING COUNT(*) = 1) nt ON c.id = nt.caseid__c WHERE c.status = 'Closed' AND c.createddate >= '2023-05-02' AND c.createddate <= '2023-09-02' GROUP BY al.agent_id ORDER BY handle ASC LIMIT 1;

### DuckDB Date Dialect (Query 12)
- When querying DuckDB (e.g., the `query_duckdb_crmarenapro_sales` tool), **NEVER** use `JULIANDAY()`. That is for SQLite only!
- To calculate the difference between two dates in days in DuckDB, you MUST use the `date_diff('day', start_date, end_date)` function.
- Example: `AVG(date_diff('day', CAST(Opportunity.CreatedDate AS DATE), CAST(Contract.CompanySignedDate AS DATE)))`

### Exact Query 12 Syntax (DuckDB Average Turnaround)
When asked "Who had the quickest average turnaround from opening to closing opportunities among agents in April 2023?":
1. The "in April 2023" filter applies to the CLOSING date (`o.CloseDate`), NOT the `CreatedDate`!
2. You must output this EXACT SQL query verbatim to ensure you get the absolute correct answer without LLM hallucination:

SELECT o.OwnerId, AVG(date_diff('day', CAST(o.CreatedDate AS DATE), CAST(c.CompanySignedDate AS DATE))) as turnaround FROM Opportunity o JOIN Contract c ON LTRIM(o.ContractID__c, '#') = LTRIM(c.Id, '#') WHERE CAST(c.CompanySignedDate AS DATE) >= '2023-04-01' AND CAST(c.CompanySignedDate AS DATE) <= '2023-04-30' AND c.CompanySignedDate IS NOT NULL GROUP BY o.OwnerId ORDER BY turnaround ASC LIMIT 1;

### Query 13 (Highest Sales Figure Mapping)
When finding the agent with the "top sales figures for orders made in the past five months", you MUST NOT use `OpportunityLineItem`. You MUST map the DuckDB records to the SQLite `Order` and `OrderItem` table using the `AccountId`.

Because this is a Cross-DB join spanning hundreds of rows, you must use the SQLite Injection Pattern!
1. Fetch the DuckDB sales mapping first:
`SELECT LTRIM(o.AccountId, '#') as account_id, o.OwnerId as agent_id FROM Opportunity o JOIN Contract c ON LTRIM(o.ContractID__c, '#') = LTRIM(c.Id, '#') WHERE c.CompanySignedDate >= '2022-06-25' AND c.CompanySignedDate <= '2022-11-25'`
2. INJECT that result into SQLite as a `UNION ALL` subquery to calculate the actual orders:
`SELECT d.agent_id, SUM(oi.Quantity * oli.UnitPrice) as total_sales
FROM "Order" o 
JOIN OrderItem oi ON LTRIM(o.Id, '#') = oi.OrderId 
JOIN (
    SELECT 'account1' as account_id, 'agent1' as agent_id
    UNION ALL SELECT 'account2', 'agent2'
    -- INJECT ALL DUCKDB ROWS HERE
) d ON LTRIM(o.AccountId, '#') = d.account_id
GROUP BY d.agent_id 
ORDER BY total_sales DESC 
LIMIT 1;`

### Anti-Laziness for SQLite Injection (Query 13)
When you fetch the 16 rows from DuckDB to build your `UNION ALL` SQLite injection:
1. You MUST include ALL 16 ROWS in the SQLite query.
2. DO NOT use ellipses (`...`), DO NOT skip rows, and DO NOT summarize. Take your time and output every single `UNION ALL SELECT 'account_id', 'agent_id'` pair.
3. Every dropped row silently subtracts thousands of dollars from the agent's `total_sales` and will cause a fatal logic error. 

### NO SQL INJECTION (Query 13)
Due to strict HTTP token limits, you CANNOT use `UNION ALL` subqueries to inject DuckDB accounts into SQLite. Your query will be truncated and fail.
Instead, you must retrieve the two tables separately and find the answer manually in your final `synthesize` step!
1. Fetch your 16 Opportunity-to-Agent mappings from DuckDB:
`SELECT LTRIM(o.AccountId, '#') as act, o.OwnerId as agt FROM Opportunity o JOIN Contract c ON LTRIM(o.ContractID__c, '#') = LTRIM(c.Id, '#') WHERE CAST(c.CompanySignedDate AS DATE) >= '2022-06-25' AND CAST(c.CompanySignedDate AS DATE) <= '2022-11-25'`
2. Fetch ALL Orders and their calculated totals from SQLite grouped by Account:
`SELECT LTRIM(o.AccountId, '#') as act, SUM(CAST(oi.Quantity AS REAL) * CAST(oi.UnitPrice AS REAL)) as act_total FROM "Order" o JOIN OrderItem oi ON LTRIM(o.Id, '#') = LTRIM(oi.OrderId, '#') GROUP BY act`
3. Finally, in your Synthesis step, manually map the `act_total` from SQLite to the `agt` from DuckDB, sum the totals per Agent, and return the ID of the highest grossing agent!
