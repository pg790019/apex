---
name: salesforce-dynamics-migration
description: Use this skill when a Jira ticket's intent is about reverse engineering Salesforce components and/or forward engineering (migrating) them to Microsoft Dynamics 365. This covers component migration, dependency-aware sequencing of migration steps, and mapping Salesforce objects to their Dynamics 365 equivalents. Do not use for unrelated requests (e.g. general coding tasks, non-Salesforce/Dynamics topics).
---

# salesforce-dynamics-migration

## Overview

This skill covers migrating Salesforce components to their Microsoft Dynamics
365 equivalents. It applies whenever a ticket's intent involves Salesforce
reverse engineering, Dynamics 365 forward engineering, or component migration
between the two platforms.

## Instructions

### 1. Identify the components in scope

Read the ticket description and comments to determine which Salesforce
components need to be migrated. If the exact list isn't explicit, look for
component names mentioned anywhere in the ticket (summary, description, or
comments) before assuming a default set.

### 2. Determine the correct migration order using dependency knowledge

Some components depend on others being migrated first. Use this known
dependency table when sequencing the plan:

| Component          | Depends on (must be migrated first) |
|---------------------|--------------------------------------|
| Account              | (none -- migrate first)             |
| Contact              | Account                             |
| Opportunity          | Account, Contact                    |
| Custom_Object__c     | Account                             |

Rules:
- Never schedule a component before all of its dependencies in the plan.
- Components with no dependencies (e.g. Account) go first.
- If a component isn't in this table, treat it as having no known
  dependencies, but explicitly flag it in the plan as "dependency unknown --
  verify before migrating" rather than silently assuming it's independent.

### 3. Use the migrate_component tool per component, in dependency order

Each plan step should correspond to one component migration, in the order
determined above. Note the dependency reasoning directly in plan.md next to
each step (e.g. "3. Migrate Opportunity (depends on Account, Contact --
both completed in steps 1-2)"), so the executor and validator can both see
*why* the order matters, not just what the order is.

### 4. Known object mapping reference

| Salesforce Object   | Dynamics 365 Equivalent |
|----------------------|--------------------------|
| Account               | Account (D365)          |
| Contact               | Contact (D365)          |
| Opportunity           | Opportunity (D365)      |
| Custom_Object__c      | Custom Entity (D365)    |

Any component not in this table has no confirmed mapping -- flag it for
manual review rather than guessing at a Dynamics 365 equivalent.
