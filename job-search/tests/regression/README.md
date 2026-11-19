# Regression set: five known trouble cases

Frozen HiringCafe responses (retrieved 2026-11-16, public postings) that broke or bent earlier live runs in the upstream project. They are screened with the made-up New York searcher in [fixtures/criteria-nyc.yaml](../fixtures/criteria-nyc.yaml). Screening date: **2026-11-16** (the deadline and age checks depend on it).

| Job | Trouble it tests | Expected status |
|---|---|---|
| Milliman MedInsight, Senior Product Strategy Manager | Application deadline (Sep 30, 2026) already passed; "Indianapolis" once matched the excluded region "india" | `evaluation_error` |
| Zelis, Sr. Product Strategy Manager | "Morristown or Atlanta" drops the state; the posting URL says New Jersey; travel 20-25% | `eligible` or `needs_verification` |
| Chefman, Culinary Project Manager | Posted pay tops out at $80K, below the fixture's $100K floor | `excluded` |
| Regeneron, Sr Scientist | Explicit degree and years stay unresolved; inferred concerns are not mandatory knockouts | `needs_verification` |
| Thomson Reuters, Innovation Strategy Executive | Description truncated by the provider; no Greenhouse board | `evaluation_error` |

`test_run_control.RegressionSet` covers the scripted part: intake and L1. The upstream project also replays saved evaluation judgments through the full result and status path; those judgments cite the upstream owner's own records, so they are not ported, and the agent part of these cases is not tested here.
