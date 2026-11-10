# {Collection name}

[Career index](../README.md) · [Reference](../../schema/experience-schema.md)

{One paragraph: what this collection holds, where its records came from (for example "Imported from the CV on {date}; accounts keep the CV's wording until reviewed") and any rule that applies to every record here. File grouping is navigation, not ownership; relationships are arrays.}

<a id="{role-id}"></a>
## {Organization} — {Title}

```yaml
id: "{role-id}"
record_type: "role"
title: "{Title as held}"
organization: "{Organization}"
historical_names: []
role_kind: "{formal | functional}"
title_status: "{How the title is established, e.g. formal appointment confirmed / CV label}"
display_dates: "{Mon YYYY - Mon YYYY or Present}"
metadata_dates: {"start": "{MM/YYYY}", "end": "{MM/YYYY or present}"}
date_precision: "month"
verification: "{user-confirmed | cv-sourced | source-supported | unverified}"
source_path: "{Curriculum-Vitae.md or another source}"
source_revision: "{commit SHA of the CV snapshot, if imported}"
source_lines: []
associated_experiences: ["{role-id}-EXP-001"]
functions: []
capabilities: []
tools: []
current_team_context: null
limitations: []
current_clarifications: []
legacy_metadata: ""
```

<a id="{role-id}-exp-001"></a>
```yaml
id: "{role-id}-EXP-001"
record_type: "experience"
associated_roles: ["{role-id}"]
associated_projects: []
functions: []
capabilities: []
outcomes: []
current_account: "{What you did, in plain factual sentences: the situation, your part, what happened.}"
account_basis: "{Where this account comes from}"
verification: "{user-confirmed | cv-sourced | source-supported | unverified}"
scope_and_status: ["{Ownership and delivery boundaries: shared or personal, built or launched, plan or result}"]
evidence_notes: []
evidence: []
source_lines: []
current_clarifications: []
```

<a id="{role-id}-out-001"></a>
```yaml
id: "{role-id}-OUT-001"
record_type: "outcome"
title: "{Short name of the result}"
associated_experiences: ["{role-id}-EXP-001"]
verification: "{user-confirmed | cv-sourced | source-supported | unverified}"
measurement_period: null
current_interpretation: "{What the result means today and its limits for external use: unit, population, period, approximation}"
legacy_claims: []
evidence: []
```

<a id="{education-id}"></a>
## {Institution} — {Degree or credential}

```yaml
id: "{education-id}"
record_type: "{education | credentials}"
title: "{Degree, diploma, certificate or license}"
organization: "{Institution or issuer}"
display_dates: "{YYYY or Mon YYYY - Mon YYYY}"
current_account: "{Field of study, honors, notable work}"
verification: "{user-confirmed | cv-sourced | source-supported | unverified}"
functions: []
capabilities: []
limitations: ["{e.g. Certificate expired {YYYY}; not a current license}"]
```
