# Northwind Logistics roles

[Career story](../story.md) · [Roles](roles.md) · [Experiences](experiences.md)

Riley Example (fictional sample). One formal title, and two functional titles that describe the work as it grew.

<a id="nw-role-001"></a>
## NW-ROLE-001 — Operations Specialist

```yaml
id: "NW-ROLE-001"
record_type: "role"
organization_id: "NW"
organization: "Northwind Logistics"
title: "Operations Specialist"
role_kind: "formal"
title_status: "formal appointment confirmed by offer letter"
start: "2018-03"
end: "present"
date_precision: "month"
functional_role_ids: ["NW-ROLE-002", "NW-ROLE-003"]
associated_experiences: ["NW-EXP-001", "NW-EXP-002"]
current_team_context: {"verification": "user-confirmed", "managed": 3, "reports_to": "Site Director"}
verification: "user-confirmed"
limitations: ["The formal title never changed; the functional titles describe growing responsibility, not a promotion."]
```

<a id="nw-role-002"></a>
## NW-ROLE-002 — Operations Analyst

```yaml
id: "NW-ROLE-002"
record_type: "role"
organization_id: "NW"
organization: "Northwind Logistics"
title: "Operations Analyst"
role_kind: "functional"
title_status: "functional label for work performed; not a formal appointment"
formal_title_ids: ["NW-ROLE-001"]
functional_window: {"start": "2018-03", "end": "2019-02"}
associated_experiences: ["NW-EXP-001"]
verification: "user-confirmed"
```

<a id="nw-role-003"></a>
## NW-ROLE-003 — Operations Lead

```yaml
id: "NW-ROLE-003"
record_type: "role"
organization_id: "NW"
organization: "Northwind Logistics"
title: "Operations Lead"
role_kind: "functional"
title_status: "functional label for work performed; not a formal appointment"
formal_title_ids: ["NW-ROLE-001"]
functional_window: {"start": "2019-03", "end": "2024-06"}
functional_labels: ["Operations Lead", "Warehouse Operations Lead"]
functional_label_selection: "either-or"
associated_experiences: ["NW-EXP-002"]
verification: "user-confirmed"
```
