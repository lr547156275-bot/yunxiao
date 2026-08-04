# Metric definition report

- New-batch CCT: maximum completion time minus release among pending new-batch flows, in us.
- Median/max flow FCT and completion skew: median, maximum, and max-minus-min pending-flow FCT, in us.
- Peak queue: maximum sampled bottleneck queue, bytes.
- Queue AUC: integral of bottleneck queue over time, converted from byte-seconds to byte-us.
- Utilization: raw forward bottleneck transmitted-byte utilization over the simulator's recorded window, normalized by one 100 Gbit/s bottleneck. Corrected utilization clips only audit values above 1; all main tables retain raw values.
- Pre-release utilization: mean bottleneck utilization in [2 ms, 3 ms), percent.
- Incumbent drop: worst fractional throughput shortfall relative to configured incumbent offered rate.
- Planned/actual admission: sums of pending-flow planned admit rates / measured admission mean rates.
- Independent oversubscription: actual pending-flow admission sum divided by 100 Gbit/s; excess is max(ratio-1,0).
- Control metrics: summary plus grant messages/bytes; rate per configured 0.1 s simulation; DATA wire bytes use recorded application bytes plus configured 64-byte per-packet wire overhead.
- ECN/PFC and capacity/credit/pacing violations are direct recorded counts; PFC duration pairs pause/resume events.

Packets, ACKs, and control cycles are not treated as independent statistical samples. This is a deterministic one-seed parameter scan; no p-values or random-significance claims are made.
