# Suspicious findings

- fan16_msg1m_load0__bop_qb__seed1: utilization_above_100_percent = 1.0015590136986283 (audit).

The utilization above 1 is preserved raw and separately clipped only in the audit column; it is not silently substituted in performance comparisons.
