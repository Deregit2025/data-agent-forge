# CRMArena Pro — Knowledge Base Document

## 1. Dataset Overview
A Salesforce-style CRM dataset covering customer accounts, support cases, sales pipeline, products, activities, and territories for a B2B software/technology company.

---

## 2. Databases & Tables

### `query_postgres_crmarenapro` (PostgreSQL) — Support Data
- **Case**: Support tickets. Key fields: `id`, `priority` (High/Medium/Low), `status` (e.g., "Waiting on Customer", "Closed"), `contactid`, `accountid`, `ownerid`, `issueid__c`, `orderitemid__c`, `createddate`, `closeddate` (null if open).
- **casehistory__c**: Audit log of field changes on cases. Links to Case via `caseid__c`. Fields: `field__c`, `oldvalue__c`, `newvalue__c`, `createddate`.
- **emailmessage**: Emails linked to cases via `parentid` (= Case.id). Fields: `fromaddress`, `toids`, `messagedate`, `textbody`.
- **issue__c**: Issue category/type lookup. Fields: `id`, `name`, `description__c`. Linked from Case via `issueid__c`.
- **knowledge__kav**: Knowledge base articles. Fields: `title`, `summary`, `faq_answer__c`, `urlname`.
- **livechattranscript**: Chat sessions linked to cases via `caseid`, accounts via `accountid`, contacts via `contactid`. Contains full `body` text.

### `query_sqlite_crmarenapro_core` (SQLite) — Core CRM
- **Account**: Companies. Fields: `Id`, `Name`, `Industry`, `NumberOfEmployees` (REAL), `ShippingState` (2-letter US state), `Phone`, `Description`.
- **Contact**: Individuals. Links to Account via `AccountId`. Fields: `Id`, `FirstName`, `LastName`, `Email`.
- **User**: Internal agents/reps. Fields: `Id`, `FirstName`, `LastName`, `Email`, `Username`, `Alias`.

### `query_sqlite_crmarenapro_products` (SQLite) — Products & Orders
- **Product2**: Product catalog. Fields: `Id`, `Name`, `Description`, `IsActive` (0/1), `External_ID__c`.
- **Order** / **OrderItem**: Orders linked to accounts via `AccountId`; OrderItems link to Orders via `OrderId` and products via `Product2Id`. Case links to OrderItem via `orderitemid__c`.
- **Pricebook2** / **PricebookEntry**: Pricing structures with validity dates. PricebookEntry links Pricebook2 to Product2.
- **ProductCategory** / **ProductCategoryProduct**: Category taxonomy; `ProductCategoryProduct` is the junction table linking products to categories.

### `query_sqlite_crmarenapro_territory` (SQLite) — Territories
- **Territory2**: Sales territories. `Description` contains comma-separated US state abbreviations (e.g., "MO,KS,OK").
- **UserTerritory2Association**: Junction table linking `UserId` to `Territory2Id`.

### `query_duckdb_crmarenapro_activities` (DuckDB) — Activities
- **Event**: Calendar events linked to opportunities/accounts via `WhatId`, assigned via `OwnerId`. Fields: `StartDateTime`, `DurationInMinutes`, `Location`, `IsAllDayEvent` (0/1).
- **Task**: To-dos linked via `WhatId`. Fields: `Priority`, `Status`, `ActivityDate`.
- **VoiceCallTranscript__c**: Call transcripts linked to opportunities via `OpportunityId__c` and leads via `LeadId__c`.

### `query_duckdb_crmarenapro_sales` (DuckDB) — Sales
- **Opportunity**: Deals. Fields: `Amount` (DOUBLE), `StageName`, `Probability`, `CloseDate`, `ContractID__c`, `AccountId`, `ContactId`, `OwnerId`.
- **OpportunityLineItem**: Products on