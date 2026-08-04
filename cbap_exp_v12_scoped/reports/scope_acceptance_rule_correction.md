# Scope acceptance rule correction

## Why the rule changed

The scoped BYPASS path is required to account for an exact 5 us scope-decision delay. A simultaneous raw-RCT overhead limit of 1% cannot be met when the baseline RCT is below 500 us. The corrected rule retains raw RCT for performance reporting and decomposes only the acceptance check into fixed decision cost and unexplained network cost.

The timing tolerance is 0.1 us. ns-3 timestamps in these outputs are recorded to nanosecond precision, so 0.1 us safely covers one event scheduling/serialization rounding discrepancy without approaching the prohibited 1 us upper bound.

## Corrected formulas

- `network_only_rct_scoped_us = raw_rct_scoped_us - scope_decision_delay_us`
- `raw_overhead_us = raw_rct_scoped_us - dcqcn_rct_us`
- `unexplained_overhead_us = raw_overhead_us - scope_decision_delay_us`
- `network_relative_difference = abs(network_only_rct_scoped_us - dcqcn_rct_us) / dcqcn_rct_us`

## KeyError compatibility audit

`collect_run_metrics.py` now reads `subcase` with a compatibility fallback to the existing `scenario` field. It does not synthesize a new scenario and does not alter any metric. All 18 existing `result.json` files were re-read by this analyzer; none was rewritten and no ns-3 experiment was executed.

## Reused result inputs

| Path | Size (bytes) | mtime (UTC) | SHA-256 |
|---|---:|---|---|
| `runs_scope/batch_incast/cbap_full_v11_unscoped/seed_1/result.json` | 635 | 2026-08-01T11:36:54.479609+00:00 | `0c1848f1eb2070228af94c397ac46003991faea5d32b9a384ca334f76b39302a` |
| `runs_scope/batch_incast/cbap_full_v12_scoped/seed_1/result.json` | 633 | 2026-08-01T11:36:54.591609+00:00 | `97c35f999c96a4413767cda11373beac47c34829bb5fdf050858ae4c78c65343` |
| `runs_scope/batch_incast/dcqcn/seed_1/result.json` | 666 | 2026-08-01T11:36:54.707608+00:00 | `1cfec3fe193c60cdce7c5110d8802ab73a1e301a5c642472ac7e643cac10839f` |
| `runs_scope/no_shared_link/cbap_full_v11_unscoped/seed_1/result.json` | 660 | 2026-08-01T11:36:54.819607+00:00 | `6f902df93903bb1cc5df8cf083deae6ad05fbd1523797bfb244ea638746dc73e` |
| `runs_scope/no_shared_link/cbap_full_v12_scoped/seed_1/result.json` | 654 | 2026-08-01T11:36:54.923606+00:00 | `b1d2922c55d7a51f33fa1521071e02c738f265b0481b97150cb5f1d648959291` |
| `runs_scope/no_shared_link/dcqcn/seed_1/result.json` | 639 | 2026-08-01T11:36:55.027606+00:00 | `0831f9b3db70d640b0566fb7c75cda3e2418df0951cf1ba22a6b4bfccf9d842b` |
| `runs_scope/single_pending/cbap_full_v11_unscoped/seed_1/result.json` | 643 | 2026-08-01T11:36:55.139605+00:00 | `b4e23358814984f2b06bae9809692bd7b177cc7c034cfe7de1b37d9a16a1004c` |
| `runs_scope/single_pending/cbap_full_v12_scoped/seed_1/result.json` | 677 | 2026-08-01T11:36:55.247604+00:00 | `acf6479f23c7ca1931b364282f45ae1c9a01a631b32e688bf96bf216a1156d5a` |
| `runs_scope/single_pending/dcqcn/seed_1/result.json` | 615 | 2026-08-01T11:36:55.355604+00:00 | `2974cdfd9d0c6e82aa8f7aa8c44ca7c160c6e8a0dc7c91d0d5e8342d82bce275` |
| `runs_scope/synchronous_parking_lot/cbap_full_v11_unscoped/seed_1/result.json` | 652 | 2026-08-01T11:36:55.459603+00:00 | `b436ca76290092e7975784139a0d77fceefd921d2da3fb178654bcf3711ee7ac` |
| `runs_scope/synchronous_parking_lot/cbap_full_v12_scoped/seed_1/result.json` | 650 | 2026-08-01T11:36:55.539603+00:00 | `429c2cb69abea6d397fd858f175d073b2f40a74e45215433695722f4bc4eb1b9` |
| `runs_scope/synchronous_parking_lot/dcqcn/seed_1/result.json` | 655 | 2026-08-01T11:36:55.619602+00:00 | `1664387f256e7cc0ef6a38552f5349a4a60951ee44adcc0cfaea43c335c0ba42` |
| `runs_scope/two_pending_low_demand/cbap_full_v11_unscoped/seed_1/result.json` | 673 | 2026-08-01T11:36:55.699601+00:00 | `b8e3b6324f40f4ab969ba75512d55db1076e27444d374d994e8b34428f06a579` |
| `runs_scope/two_pending_low_demand/cbap_full_v12_scoped/seed_1/result.json` | 671 | 2026-08-01T11:36:55.783601+00:00 | `3205c4defb35d3ea334dbdfdb04c2b86921221b558ae6b87447cc30d832d61a9` |
| `runs_scope/two_pending_low_demand/dcqcn/seed_1/result.json` | 670 | 2026-08-01T11:36:55.871600+00:00 | `fd40fb0889491b8f79c79ec48bda6d780372c597ef475b09b1fa5fa5affaff03` |
| `runs_scope/two_pending_overload/cbap_full_v11_unscoped/seed_1/result.json` | 682 | 2026-08-01T11:36:55.955600+00:00 | `8b515d3f36a50d9d413bb5c33322b9e85a7f6959582e925f8a0888150373c06f` |
| `runs_scope/two_pending_overload/cbap_full_v12_scoped/seed_1/result.json` | 680 | 2026-08-01T11:36:56.039599+00:00 | `de29190db34da478bcc1322c5d17b83b31005f5eb81c39c2cae73cdbbad5cc79` |
| `runs_scope/two_pending_overload/dcqcn/seed_1/result.json` | 682 | 2026-08-01T11:36:56.123599+00:00 | `1da0a19a9c6c424978b88dbfb756aeaa041ddb04fa9e0a3edfc21bf5d90525e2` |

## Outcome

- Reused results: 18/18
- New ns-3 runs: 0
- Final status: `SCOPE_REGRESSION_PASS`
