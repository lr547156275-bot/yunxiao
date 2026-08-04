#!/usr/bin/env python3
import json
import os
from mainlib import CASES, base_config, flow_sizes, scenarios, write_round_inputs
from mainlib import write_topology


def main():
    os.makedirs(CASES, exist_ok=True)
    for name, spec in scenarios().items():
        case_dir = os.path.join(CASES, name)
        os.makedirs(case_dir, exist_ok=True)
        receiver, bottleneck = write_topology(case_dir, int(spec["senders"]))
        write_round_inputs(case_dir, spec, 1)
        with open(os.path.join(case_dir, "config.txt"), "w") as handle:
            handle.write(base_config(spec, bottleneck))
        sizes = flow_sizes(spec)
        meta = dict(spec)
        meta.update({
            "receiver": receiver,
            "selected_bottleneck": "%d:1" % bottleneck,
            "line_rate_bps": 100000000000,
            "packet_payload_bytes": 1000,
            "jitter_bound_ns": 5000,
            "jitter_policy": ("uniform_[0,+5us]_barrier_safe"
                              if int(spec["compute_gap_us"]) == 0 else
                              "uniform_[-5us,+5us]"),
            "fixed_ecmp": True,
            "global_barrier": True,
            "same_qp_rounds": True,
            "primer_enabled": False,
            "background_enabled": False,
            "message_bytes_by_sender": sizes,
        })
        with open(os.path.join(case_dir, "scenario_meta.json"), "w") as handle:
            json.dump(meta, handle, indent=2, sort_keys=True)
            handle.write("\n")


if __name__ == "__main__":
    main()
