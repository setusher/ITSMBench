# Live sweep: null agent + oracle x2 on every task

Source: `sweep.jsonl`. Emulator: the digest pinned in the repo README. Verifier: each task's own tests (pytest 8.4.1 / grade.js).

## Headline numbers

- tasks swept: 89 (infra errors: 0)
- oracle gets reward 1 on both runs: 87/89
- oracle fails: 2 -> task-ep-14, task-ep-9
- two oracle runs disagree on some check (flaky): 0 -> none
- null agent gets reward 1: 0 -> none
- tasks where a non-guard-looking check passes with NO agent action: 12 (name heuristic; review each)

| task | checks passing on the untouched world (non-guard names) |
|---|---|
| task-alloc-4 | test_cap_respected |
| task-alloc-5 | test_day_covered[4], test_override_users_within_allowed_set |
| task-ep-10 | TestOraclePlanKeys::test_a_notes_page_exists, TestOraclePlanKeys::test_a_trigger_issue_exists, TestPatchRelease::test_d_patch_notes_excludes_unfixed_keys |
| task-ep-16 | test_p11_decommissioned_job_stays_disabled |
| task-ep-17 | test_G_anti_greenwash_cc81_folder_empty |
| task-ep-22 | test_a_pd_billing_resolved, test_a_cmdb_cutover_ord1_retired |
| task-ep-5 | test_g_dana_report_stays_in_submission_folder, test_g_vp180_file_stays_archived, test_g_vp180_row_stays_archived, test_g_tom_files_never_moved, test_g_fmea_sibling_pages_unmoved, test_g_other_archived_channels_stay_archived |
| task-ep-7 | test_b3_lying_fp_threat_incident_resolved, test_b3b_exfil_host_beacon_incident_resolved, test_g4b_stale_box_stays_isolated |
| task-ep-9 | test_g_mobile_legacy_stays_disabled, test_g_postmortem_page_exists |
| task-grc-3 | test_app_access_revoked_1, test_app_access_revoked_2, test_app_access_revoked_3 |
| task-n-15 | test_approved_external_deps_in_service |
| task-net-1 | test_zia_activation_active |

## Per task

| task | family | null agent | oracle runs | oracle repeatable | non-guard checks passing for null |
|---|---|---|---|---|---|
| task-a-1 | pytest | 2/20 | 20/20 , 20/20 | yes | - |
| task-a-2 | pytest | 2/20 | 20/20 , 20/20 | yes | - |
| task-a-31 | pytest | 0/28 | 28/28 , 28/28 | yes | - |
| task-a-32 | pytest | 0/13 | 13/13 , 13/13 | yes | - |
| task-a-33 | pytest | 0/34 | 34/34 , 34/34 | yes | - |
| task-a-35 | pytest | 0/29 | 29/29 , 29/29 | yes | - |
| task-a-36 | pytest | 0/32 | 32/32 , 32/32 | yes | - |
| task-a-37 | pytest | 0/29 | 29/29 , 29/29 | yes | - |
| task-a-38 | pytest | 0/26 | 26/26 , 26/26 | yes | - |
| task-a-40 | pytest | 0/34 | 34/34 , 34/34 | yes | - |
| task-a-5 | pytest | 2/20 | 20/20 , 20/20 | yes | - |
| task-alloc-3 | pytest | 11/29 | 29/29 , 29/29 | yes | - |
| task-alloc-4 | pytest | 7/12 | 12/12 , 12/12 | yes | test_cap_respected |
| task-alloc-5 | pytest | 10/15 | 15/15 , 15/15 | yes | test_day_covered[4], test_override_users_within_allowed_set |
| task-alloc-6 | pytest | 13/21 | 21/21 , 21/21 | yes | - |
| task-b1 | assertions | 0/9 | 9/9 , 9/9 | yes | - |
| task-b10 | assertions | 0/14 | 14/14 , 14/14 | yes | - |
| task-b11 | assertions | 0/15 | 15/15 , 15/15 | yes | - |
| task-b2 | assertions | 0/14 | 14/14 , 14/14 | yes | - |
| task-b3 | assertions | 0/6 | 6/6 , 6/6 | yes | - |
| task-b4 | assertions | 0/14 | 14/14 , 14/14 | yes | - |
| task-b5 | assertions | 0/17 | 17/17 , 17/17 | yes | - |
| task-b6 | assertions | 0/14 | 14/14 , 14/14 | yes | - |
| task-b7 | assertions | 0/14 | 14/14 , 14/14 | yes | - |
| task-b8 | assertions | 0/16 | 16/16 , 16/16 | yes | - |
| task-b9 | assertions | 0/14 | 14/14 , 14/14 | yes | - |
| task-c1 | assertions | 0/17 | 17/17 , 17/17 | yes | - |
| task-c2 | assertions | 0/6 | 6/6 , 6/6 | yes | - |
| task-c3 | assertions | 0/14 | 14/14 , 14/14 | yes | - |
| task-c4 | assertions | 0/16 | 16/16 , 16/16 | yes | - |
| task-c5 | assertions | 0/17 | 17/17 , 17/17 | yes | - |
| task-ep-1 | pytest | 8/33 | 33/33 , 33/33 | yes | - |
| task-ep-10 | pytest | 12/26 | 26/26 , 26/26 | yes | TestOraclePlanKeys::test_a_notes_page_exists, TestOraclePlanKeys::test_a_trigger_issue_exists, TestPatchRelease::test_d_patch_notes_excludes_unfixed_keys |
| task-ep-11 | pytest | 5/12 | 12/12 , 12/12 | yes | - |
| task-ep-13 | pytest | 8/24 | 24/24 , 24/24 | yes | - |
| task-ep-14 | pytest | 11/24 | 11/24 , 11/24 | yes | - |
| task-ep-15 | pytest | 5/12 | 12/12 , 12/12 | yes | - |
| task-ep-16 | pytest | 11/17 | 17/17 , 17/17 | yes | test_p11_decommissioned_job_stays_disabled |
| task-ep-17 | pytest | 14/21 | 21/21 , 21/21 | yes | test_G_anti_greenwash_cc81_folder_empty |
| task-ep-18 | pytest | 10/18 | 18/18 , 18/18 | yes | - |
| task-ep-19 | pytest | 6/15 | 15/15 , 15/15 | yes | - |
| task-ep-2 | pytest | 19/36 | 36/36 , 36/36 | yes | - |
| task-ep-20 | pytest | 17/26 | 26/26 , 26/26 | yes | - |
| task-ep-21 | pytest | 13/26 | 26/26 , 26/26 | yes | - |
| task-ep-22 | pytest | 8/23 | 23/23 , 23/23 | yes | test_a_pd_billing_resolved, test_a_cmdb_cutover_ord1_retired |
| task-ep-23 | pytest | 14/29 | 29/29 , 29/29 | yes | - |
| task-ep-24 | pytest | 11/24 | 24/24 , 24/24 | yes | - |
| task-ep-25 | pytest | 6/13 | 13/13 , 13/13 | yes | - |
| task-ep-4 | pytest | 4/10 | 10/10 , 10/10 | yes | - |
| task-ep-5 | pytest | 20/47 | 47/47 , 47/47 | yes | test_g_dana_report_stays_in_submission_folder, test_g_vp180_file_stays_archived, test_g_vp180_row_stays_archived |
| task-ep-7 | pytest | 16/42 | 42/42 , 42/42 | yes | test_b3_lying_fp_threat_incident_resolved, test_b3b_exfil_host_beacon_incident_resolved, test_g4b_stale_box_stays_isolated |
| task-ep-8 | pytest | 8/30 | 30/30 , 30/30 | yes | - |
| task-ep-9 | pytest | 16/26 | 16/26 , 16/26 | yes | test_g_mobile_legacy_stays_disabled, test_g_postmortem_page_exists |
| task-grc-2 | pytest | 0/19 | 19/19 , 19/19 | yes | - |
| task-grc-3 | pytest | 3/18 | 18/18 , 18/18 | yes | test_app_access_revoked_1, test_app_access_revoked_2, test_app_access_revoked_3 |
| task-grc-4 | pytest | 0/20 | 20/20 , 20/20 | yes | - |
| task-grc-5 | pytest | 0/24 | 24/24 , 24/24 | yes | - |
| task-grc-6 | pytest | 0/17 | 17/17 , 17/17 | yes | - |
| task-grc-7 | pytest | 0/20 | 20/20 , 20/20 | yes | - |
| task-grc-8 | pytest | 0/18 | 18/18 , 18/18 | yes | - |
| task-iam-12 | pytest | 0/25 | 25/25 , 25/25 | yes | - |
| task-iam-13 | pytest | 0/22 | 22/22 , 22/22 | yes | - |
| task-iam-14 | pytest | 0/21 | 21/21 , 21/21 | yes | - |
| task-iam-15 | pytest | 0/21 | 21/21 , 21/21 | yes | - |
| task-iam-16 | pytest | 0/19 | 19/19 , 19/19 | yes | - |
| task-iam-17 | pytest | 0/30 | 30/30 , 30/30 | yes | - |
| task-iam-18 | pytest | 9/29 | 29/29 , 29/29 | yes | - |
| task-iam-19 | pytest | 0/28 | 28/28 , 28/28 | yes | - |
| task-iam-20 | pytest | 18/37 | 37/37 , 37/37 | yes | - |
| task-n-1 | pytest | 0/25 | 25/25 , 25/25 | yes | - |
| task-n-10 | pytest | 0/21 | 21/21 , 21/21 | yes | - |
| task-n-11 | pytest | 0/31 | 31/31 , 31/31 | yes | - |
| task-n-12 | pytest | 0/25 | 25/25 , 25/25 | yes | - |
| task-n-13 | pytest | 0/23 | 23/23 , 23/23 | yes | - |
| task-n-14 | pytest | 0/37 | 37/37 , 37/37 | yes | - |
| task-n-15 | pytest | 36/112 | 112/112 , 112/112 | yes | test_approved_external_deps_in_service |
| task-n-2 | pytest | 0/21 | 21/21 , 21/21 | yes | - |
| task-n-3 | pytest | 0/22 | 22/22 , 22/22 | yes | - |
| task-n-4 | pytest | 9/35 | 35/35 , 35/35 | yes | - |
| task-n-5 | pytest | 0/21 | 21/21 , 21/21 | yes | - |
| task-n-6 | pytest | 0/24 | 24/24 , 24/24 | yes | - |
| task-n-7 | pytest | 0/23 | 23/23 , 23/23 | yes | - |
| task-n-8 | pytest | 0/23 | 23/23 , 23/23 | yes | - |
| task-net-1 | pytest | 13/31 | 31/31 , 31/31 | yes | test_zia_activation_active |
| task-ops-1 | pytest | 0/27 | 27/27 , 27/27 | yes | - |
| task-ops-2 | pytest | 0/20 | 20/20 , 20/20 | yes | - |
| task-ops-3 | pytest | 0/20 | 20/20 , 20/20 | yes | - |
| task-ops-4 | pytest | 0/24 | 24/24 , 24/24 | yes | - |
| task-ops-5 | pytest | 0/18 | 18/18 , 18/18 | yes | - |
