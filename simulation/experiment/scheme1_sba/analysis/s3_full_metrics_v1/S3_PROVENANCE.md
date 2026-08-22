# S3 PROVENANCE

## Selected inputs (chosen by config/SHA evidence, NOT directory name)

| arm | directory | why selected |
|---|---|---|
| CBAP-SBA rho=0.90 | `ckpt4_cbap_s3_out` | CC_MODE 30, CBAP_ENABLE 1, MIGRATION_ENABLE 1, CORE_INITIAL_RELEASE 1, INITIAL_RELEASE_RATIO 0.90, MIGRATION_TRACE 1; CBAP_MIG=1050; exit=0; 64/64 incast |
| DCQCN baseline | `ckpt4_dcqcn_s3_out` | CC_MODE 1, CBAP_ENABLE 0, zero CBAP keys; exit=0; 64/64 incast |

Rejected candidates:
- `rec2_s3_on_out` - same rho/migration and CBAP_MIG=1050, but from a different
  batch under binary 265fe2a1 with a duplicated MIGRATION_TRACE key; not a
  config-matched pair member.
- `ckpt3_cbap_s3_out` / `ckpt3_dcqcn_s3_out` - reallocation OFF
  (ABLATION_FULL_CAPACITY_REALLOCATION_OFF), CBAP_MIG=0.
- `ckpt4_cbap_s3_out.NOTRACE` - correct physics but MIGRATION_TRACE absent, so no
  direct migration trajectory; retained as bypass-consistency evidence.

## Pairing verification

All five inputs byte-identical across arms:

| input | sha256 (16) |
|---|---|
| topology.txt | 6091d5ec28c391c0 |
| s3_flow.txt | 6b922c67e56c04aa |
| s3_round_schedule.txt | 8a40b3d13abe225d |
| s3_cbap_link.txt | 70903775ca19226b |
| s3_cbap_path.txt | 1557487d29e7efb5 |

Non-algorithm config diff: **IDENTICAL** (only CC_MODE, CBAP_ENABLE,
CBAP_QUEUE_CONTROLLER_ENABLE and the three reallocation keys differ).
SIM_SEED=2 both arms.  pg: all 65 flows pg=3, pg0_count=0.

Parsed-value echo from the CBAP run.log (not config text):
`CBAP_REALLOC_PARSED migration_enable=1 core_initial_release=1 initial_release_ratio=0.9 migration_trace=1`

## Toolchain
binary `290cb41fec981bc848cbfd518257ce2c5df1384d52f2325d67955acaabd880b7`
libns3 `c643f5cc332e02763946b01b8aa1cc17c50daf4dda53a371c13e4576525eb122`

## Windows
| window | definition | value |
|---|---|---|
| W0 FULL_RUN | whole sim | 0 - 3.0 s |
| W1 CBAP | native batch | [2.000000000, 2.059406587] s |
| W1 DCQCN | native batch | [2.000000000, 2.058372997] s |
| W2 COMMON_OVERLAP | max(start), min(finish) | [2.000000000, 2.058372997] s = **58.372997 ms** |
| W3 CBAP_TAIL | DCQCN finish -> CBAP finish | [2.058372997, 2.059406587] s = **1.033590 ms** |
| W4 MIGRATION_CONVERGENCE | first CBAP_MIG -> end=converged | see S3_FULL_METRICS.csv |
