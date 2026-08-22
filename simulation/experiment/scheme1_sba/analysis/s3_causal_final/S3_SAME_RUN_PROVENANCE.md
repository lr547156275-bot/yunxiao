# S3 SAME-RUN PROVENANCE

## Cross-run diagnostic ELIMINATED

Both arms re-run under the **same binary** as the audited ckpt4 pair, with only
trace keys added.

| asset | sha256 |
|---|---|
| binary `build/scratch/third` | `290cb41fec981bc848cbfd518257ce2c5df1384d52f2325d67955acaabd880b7` |
| libns3 | `c643f5cc332e02763946b01b8aa1cc17c50daf4dda53a371c13e4576525eb122` |
| third.cc | `dd54dee455cbe9f7269186facc9a3ac688fb83785be7aab97bc95b29f57be831` |
| tx-serialization-recorder-ml.h | `4b9a4098a6d31625e46d24cfd371956cfb1a3bb9c98bbc327a7de332c0ce4b10` |
| sr_cbap_s3.txt | `d41602a8812088a6c921d1bde7257f1a6d2105342978a54067b03e982750e254` |
| sr_dcqcn_s3.txt | `741e6f99d7d74799680467b3df91c1ecc40ee374bda257f434331c7eca7fc9f2` |
| topology.txt | `6091d5ec28c391c0c8ec79dcaf035d7deb44c2dd57e4c357dffe6bafe8c4fff8` |
| s3_flow.txt | `6b922c67e56c04aa32f67078c89bd8a0a0fafceae58f078bfa272cc8223ada0b` |
| s3_cbap_link.txt | `70903775ca19226b39b3870a25fe748a2fc591bac3d5da4198c22df887e5b4df` |
| s3_cbap_path.txt | `1557487d29e7efb585a37c34ca8056767d5369f510c2bcaf26bed1b1bff649e3` |
| s3_round_schedule.txt | `8a40b3d13abe225d745360e5db26ccf71253837486b43a14423d65e9827200bb` |

Config diff vs ckpt4, CBAP arm: **only** `CBAP_ACTUATION_FILE` and
`TX_SERIALIZATION_TRACE_FILE` added.  DCQCN arm: **only**
`TX_SERIALIZATION_TRACE_FILE` added.  SIM_SEED=2 both arms.

## Byte-identity against the ckpt4 reference

**27 files compared, 27 identical, 0 differ.**

| arm | file | identical |
|---|---|---|
| CBAP | `flow_summary.csv` | YES |
| CBAP | `round_summary.csv` | YES |
| CBAP | `pfc_events.csv` | YES |
| CBAP | `selected_link_timeseries.csv` | YES |
| CBAP | `qc_trace.csv` | YES |
| CBAP | `controller_summary.csv` | YES |
| CBAP | `flow_plan.csv` | YES |
| CBAP | `selected_flow_timeseries.csv` | YES |
| CBAP | `qlen.txt` | YES |
| CBAP | `port_summary.csv` | YES |
| CBAP | `admission.csv` | YES |
| CBAP | `sba_events.csv` | YES |
| CBAP | `applied_rate_audit.csv` | YES |
| CBAP | `increase_audit.csv` | YES |
| CBAP | `feedback_summary.csv` | YES |
| CBAP | `group_round_summary.csv` | YES |
| DCQCN | `flow_summary.csv` | YES |
| DCQCN | `round_summary.csv` | YES |
| DCQCN | `pfc_events.csv` | YES |
| DCQCN | `selected_link_timeseries.csv` | YES |
| DCQCN | `qc_trace.csv` | YES |
| DCQCN | `controller_summary.csv` | YES |
| DCQCN | `flow_plan.csv` | YES |
| DCQCN | `selected_flow_timeseries.csv` | YES |
| DCQCN | `qlen.txt` | YES |
| DCQCN | `feedback_summary.csv` | YES |
| DCQCN | `group_round_summary.csv` | YES |

Includes flow_summary.csv (hence all per-flow FCTs), round_summary.csv,
pfc_events.csv, selected_link_timeseries.csv (queue), qc_trace.csv,
port_summary.csv, admission.csv, applied_rate_audit.csv, qlen.txt.

**Adding the trace keys changed nothing.**  Every result below is therefore a
SAME-RUN measurement, not a cross-run diagnostic.

## Windows (from the same-run pair)

| window | interval | duration |
|---|---|---|
| W1 CBAP | [2.000000000, 2.059406587] | 59.406587 ms |
| W1 DCQCN | [2.000000000, 2.058372997] | 58.372997 ms |
| W2 COMMON | [2.000000000, 2.058372997] | 58.372997 ms |
| W3 CBAP tail | [2.058372997, 2.059406587] | **1.033590 ms** |
