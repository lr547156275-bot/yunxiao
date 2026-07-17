# Moderate-2to1-Incast-RDMA-CC-Benchmark

This folder contains input files for `simulation/scratch/third.cc`.

## Node Mapping

- Hosts: `H0` to `H47` map to node IDs `0` to `47`.
- Leafs: `L0` to `L11` map to node IDs `48` to `59`.
- Spines: `S0` to `S3` map to node IDs `60` to `63`.

The topology is a two-layer Clos:

- Each leaf connects 4 hosts at `10Gbps`, `1us`.
- Each leaf connects all 4 spines at `10Gbps`, `2us`.
- Total nodes: 64.
- Total switches: 16.
- Total links: 96.

## Files

- `topology.txt`: shared topology.
- `flow.txt`: 8 long flows plus 32 short flows, all on PG3.
- `trace.txt`: traces L0 and selected receiver/sender hosts.
- `config_dcqcn.txt`: DCQCN / Mellanox DCQCN, `CC_MODE 1`.
- `config_hpcc.txt`: HPCC, `CC_MODE 3`.
- `config_hpcc_pint.txt`: HPCC-PINT, `CC_MODE 10`.
- `config_dctcp.txt`: DCTCP, `CC_MODE 8`.
- `config_timely.txt`: TIMELY, `CC_MODE 7`.

## Flow Summary

Long flows start at `0.010s`, size `512MiB = 536870912B`:

- `H4,H20 -> H0`
- `H8,H24 -> H1`
- `H12,H28 -> H2`
- `H16,H32 -> H3`

Short flows start at `0.050s + i * 0.002s`, size `256KiB = 262144B`:

- `Source = H(4+i)`
- `Destination = H(i mod 4)`
- `i = 0..31`

## Running

From the repository's `simulation` directory:

```bash
./waf --run "scratch/third my/config_hpcc.txt"
./waf --run "scratch/third my/config_dcqcn.txt"
./waf --run "scratch/third my/config_hpcc_pint.txt"
./waf --run "scratch/third my/config_dctcp.txt"
./waf --run "scratch/third my/config_timely.txt"
```

## Configuration Notes

The ECN maps are encoded as:

- `KMIN_MAP 1 10000000000 64`
- `KMAX_MAP 1 10000000000 128`
- `pmax = 1.0`

`third.cc` multiplies `kmin/kmax` by `1000`, so the actual ECN thresholds are:

- `kmin = 64000B`
- `kmax = 128000B`

PFC uses the existing dynamic-threshold implementation:

```text
BUFFER_SIZE 4
USE_DYNAMIC_PFC_THRESHOLD 1
```

With this topology, the dynamic PFC threshold is roughly around `500KB` per ingress port/queue. The resume behavior follows the hardcoded `SwitchMmu::resume_offset`.

`third.cc` accepts one total switch `BUFFER_SIZE` value in MB and applies it to every switch.

`QLEN_MON_START` and `QLEN_MON_END` are configured as `0` to `1.200s`. The current code has `qlen_mon_interval = 100ns` hardcoded, and `qlen_dump_interval` has been changed to `100us`.

Sending-rate and throughput sampling intervals are not supported directly by `third.cc` input files. Packet-level trace is enabled for the selected nodes instead.
