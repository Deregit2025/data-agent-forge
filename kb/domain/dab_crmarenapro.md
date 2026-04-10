# DataAgentBench: CRM Arena Pro Domain Schema & Known Patterns

## Databases
This domain (`crmarenapro`) requires querying across *six* distinct databases spanning SQLite, DuckDB, PostgreSQL, and MongoDB.

### 1. `core_crm` (SQLite)
Contains core CRM data.
**Tables:**
- `User`: Sales team info (Id, FirstName, LastName, Email, Phone, Username...)
- `Account`: Company/customer data (Id, Name, Phone, Industry, Description, NumberOfEmployees, ShippingState)
- `Contact`: Individual contacts (Id, FirstName, LastName, Email, AccountId)

### 2. `sales_pipeline` (DuckDB)
Contains opportunities, quotes, contracts, and leads.
**Tables:**
- `Contract`: Id, AccountId, Status, StartDate, CustomerSignedDate...
- `Lead`: Id, FirstName, LastName, Email, Phone, Company, Status...
- `Opportunity`: Id, ContractID__c, AccountId, ContactId...
- `OpportunityLineItem`, `Quote`, `QuoteLineItem`

### 3. `support` (PostgreSQL)
Contains customer support data.

*(Add more layers as introspected from db_description)*

## Known Query Patterns & Edge Cases
1. **Extreme Cross-Database Routing:** The agent must identify which of the 6 databases holds the exact piece of the CRM.
2. **Standard Salesforce Joins:** `AccountId`, `ContactId`, etc. are generally used as join keys across the SQLite, DuckDB, and PostgreSQL tables.
