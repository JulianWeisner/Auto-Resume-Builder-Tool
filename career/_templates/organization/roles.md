---
schema_version: "0.2"
record_type: "role_collection"
organization_id: "{ORG}"
status: "prototype"
visibility: "internal"
---

# {Organization} roles

[Career story](../story.md) · [Roles](roles.md) · [Projects](projects.md) · [Experiences](experiences.md)

{Formal titles and the functional titles that describe the work you actually did, with the date window each may be used on résumés. When the work outgrew the title, record both: the formal appointment stays true, and the functional role says what you did. Never sum overlapping roles or teams.}

<a id="{org}-role-001"></a>
## {ORG}-ROLE-001 — {Formal title}

```yaml
id: "{ORG}-ROLE-001"
record_type: "role"
organization_id: "{ORG}"
title: "{Formal title}"
role_kind: "formal"
title_status: "{e.g. formal appointment confirmed by offer letter}"
title_status_verification: "{user-confirmed | source-supported}"
relationship: "{employee | contractor | consulting}"
start: "{YYYY-MM}"
end: "{YYYY-MM or null}"
date_precision: "month"
functional_role_ids: ["{ORG}-ROLE-002"]
associated_projects: []
associated_experiences: []
current_team_context: {"verification": "{...}", "managed": null, "collaborated": null, "reports_to": "{Title, not name}"}
verification: "{user-confirmed | cv-sourced | source-supported}"
visibility: "internal"
evidence: []
```

<a id="{org}-role-002"></a>
## {ORG}-ROLE-002 — {Functional title}

```yaml
id: "{ORG}-ROLE-002"
record_type: "role"
organization_id: "{ORG}"
title: "{Functional title}"
role_kind: "functional"
title_status: "functional label for work performed; not a formal appointment"
formal_title_ids: ["{ORG}-ROLE-001"]
functional_window: {"start": "{YYYY-MM}", "end": "{YYYY-MM}"}
functional_labels: ["{Alternative label}", "{Alternative label}"]
functional_label_selection: "either-or"
associated_projects: []
associated_experiences: []
verification: "user-confirmed"
visibility: "internal"
evidence: []
```
