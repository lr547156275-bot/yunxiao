# n32 DCQCN deterministic replay report

## Verdict

`N32_CURRENT_CONFIG_DETERMINISTIC`

The current frozen `n32_64k_g50 / dcqcn` configuration was replayed for seeds
1, 2, and 3 from byte-identical main-v1 inputs. All three runs passed:

- topology, flow, rounds, fixed-path, trace, and config hashes: exact;
- frozen DCQCN algorithm source hash: exact;
- DATA, derived ACK, and recorded CNP packet counts: exact;
- maximum group RCT and flow FCT difference: 0 ns;
- maximum queue difference: 0 B;
- ECN marks: exact.

ACK counts use the audited equivalence valid for this manifest:
`L2_ACK_INTERVAL=1`, lossless inputs, hence one receiver ACK per DATA packet.
The incomplete historical 213-us result is excluded from this determination.

The machine-readable evidence is
`bop_exp/main_v2/analysis/n32_dcqcn_replay.csv`.
