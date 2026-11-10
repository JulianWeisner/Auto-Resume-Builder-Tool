---
schema_version: "0.2"
record_type: "experience_collection"
organization_id: "{ORG}"
status: "prototype"
visibility: "internal"
---

# {Organization} experiences and outcomes

[Career story](../story.md) · [Roles](roles.md) · [Projects](projects.md) · [Experiences](experiences.md)

{The maintained accounts of what you did here, and the outcome records they support. This is the evidence agents write résumé bullets from.}

<a id="{org}-exp-001"></a>
## {ORG}-EXP-001 — {Short title of the experience}

```yaml
id: "{ORG}-EXP-001"
record_type: "experience"
organization_id: "{ORG}"
title: "{Short title}"
date: null
date_note: ""
associated_roles: ["{ORG}-ROLE-001"]
associated_projects: []
related_experiences: []
functions: []
capabilities: []
outcomes: ["{ORG}-OUT-001"]
current_account: "{What you did, in plain factual sentences}"
account_basis: "{Where this account comes from}"
scope_and_status: ["{Ownership and delivery boundaries}"]
evidence_notes: []
release_status: null
verification: "{user-confirmed | cv-sourced | source-supported}"
visibility: "internal"
evidence: []
```

<a id="{org}-out-001"></a>
## {ORG}-OUT-001 — {Short name of the result}

```yaml
id: "{ORG}-OUT-001"
record_type: "outcome"
title: "{Short name}"
associated_experiences: ["{ORG}-EXP-001"]
verification: "{user-confirmed | cv-sourced | source-supported}"
visibility: "internal"
measurement_period: null
current_interpretation: "{What the result means today and its limits}"
legacy_claims: []
evidence: []
```
