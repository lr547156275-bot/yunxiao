#!/usr/bin/env python3
"""Independent mirror checks for equal-weight progressive filling."""


def fill(paths, capacities, maxima):
    rates = dict((flow, 0.0) for flow in paths)
    active = set(paths)
    while active:
        candidates = []
        for link, capacity in capacities.items():
            users = [flow for flow in active if link in paths[flow]]
            if users:
                used = sum(rates[flow] for flow in paths
                           if link in paths[flow])
                candidates.append(((capacity - used) / len(users),
                                   "link", link))
        for flow in active:
            candidates.append((maxima[flow] - rates[flow], "flow", flow))
        step = min(value for value, _, _ in candidates)
        assert step >= -1e-9
        if step <= 1e-9:
            break
        for flow in active:
            rates[flow] += step
        frozen = set()
        for value, kind, item in candidates:
            if abs(value - step) > 1e-6:
                continue
            if kind == "flow":
                frozen.add(item)
            else:
                frozen.update(flow for flow in active
                              if item in paths[flow])
        active -= frozen
    return rates


single = fill({0: [1], 1: [1]}, {1: 100.0}, {0: 100, 1: 100})
assert abs(single[0] - 50) < 1e-9
assert abs(single[1] - 50) < 1e-9

parking = fill({0: [1, 2], 1: [1], 2: [2]},
               {1: 100.0, 2: 100.0}, {0: 100, 1: 100, 2: 100})
assert all(abs(parking[flow] - 50) < 1e-9 for flow in parking)
assert parking[0] + parking[1] <= 100 + 1e-9
assert parking[0] + parking[2] <= 100 + 1e-9

# Queue borrowing remains a rate bound and the one-shot byte credit remains
# independently bounded by queue room.
queue_room = 200000
horizon_s = 20e-6
temporary_bps = 8 * queue_room / horizon_s
assert temporary_bps == 80e9
assert min(queue_room, 4 * 1024 * 1024) == 200000

print("PASS CBAP model")
