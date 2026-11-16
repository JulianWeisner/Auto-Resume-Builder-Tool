# Northwind Logistics experiences and outcomes

[Career story](../story.md) · [Roles](roles.md) · [Experiences](experiences.md)

Riley Example (fictional sample).

<a id="nw-exp-001"></a>
## NW-EXP-001 — Dock-to-stock reporting

```yaml
id: "NW-EXP-001"
record_type: "experience"
organization_id: "NW"
title: "Dock-to-stock reporting"
associated_roles: ["NW-ROLE-001", "NW-ROLE-002"]
associated_projects: []
related_experiences: ["NW-EXP-002"]
functions: ["FN-analytics"]
capabilities: ["CAP-sql-reporting"]
outcomes: []
current_account: "Wrote the SQL reports that measured dock-to-stock time for each inbound shift in Manhattan WMS. The site director used them in the weekly operations review."
account_basis: "Riley's firsthand account"
verification: "user-confirmed"
```

<a id="nw-exp-002"></a>
## NW-EXP-002 — Returns process redesign

```yaml
id: "NW-EXP-002"
record_type: "experience"
organization_id: "NW"
title: "Returns process redesign"
associated_roles: ["NW-ROLE-001", "NW-ROLE-003"]
associated_projects: []
related_experiences: ["NW-EXP-001"]
functions: ["FN-operations"]
capabilities: ["CAP-process-design", "CAP-team-leadership"]
outcomes: ["NW-OUT-001"]
current_account: "Redesigned the warehouse returns process with three shift supervisors: one inspection station, a reason code at intake and a daily restock run. Average return processing time fell from five days to two."
account_basis: "Riley's firsthand account"
scope_and_status: ["Shared with three shift supervisors; Riley led the redesign and trained the teams."]
verification: "user-confirmed"
```

<a id="nw-out-001"></a>
## NW-OUT-001 — Return processing time

```yaml
id: "NW-OUT-001"
record_type: "outcome"
title: "Return processing time"
associated_experiences: ["NW-EXP-002"]
verification: "user-confirmed"
measurement_period: "first half of 2021"
current_interpretation: "Average days from a return arriving at the dock to its restock decision, five to two. Measured from the WMS for the main site only; the second site was not included."
legacy_claims: []
```
