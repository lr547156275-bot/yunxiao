# Metric definition specification

`flow_outcome_ledger.csv` is the complete planned-flow population. Completion requires completion evidence and acknowledged application bytes greater than or equal to planned bytes. Missing completion rows remain censored. Newcomer CCT starts at batch application-ready time and therefore includes Scope and Admission Hold. Completed all-work makespan ends at the final completed flow; incomplete work has a null makespan and an observation-horizon censored lower bound.

Queue AUC uses trapezoidal integration over recorded timestamps. Time-weighted queue P95 weights each left-continuous sample by its actual following interval. Utilization from transmitted bytes and sampled utilization are reported separately. Multi-link byte utilization uses the aggregate monitored-link capacity denominator. Monitoring-only summaries are not counted as network control messages.
