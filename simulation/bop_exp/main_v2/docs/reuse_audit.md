# Main-v2 reuse audit

No main-v1 run is copied, moved, edited, or relabeled in place. Main-v2 stores
only references and validation facts in `config/reuse_manifest.csv`.

For each of the 273 formal entries the validator checks scenario, algorithm,
seed, completion state, CC mode, frozen control-source hash, topology/flow/
round/fixed-path hashes, canonical algorithm/config hash, payload size,
ECN/PFC settings, 100 Gbit/s link rate, ACK settings, and fixed-ECMP metadata.
The current audit accepts 273/273. A future mutation of an input or metadata
field changes the recomputed manifest and causes the checker to reject reuse.

The source hash is the hash of the frozen RDMA congestion-control
implementation listed by the algorithm registry. The event instrumentation
added for main-v2 is default-off, observational, and outside the frozen
control implementation. The four hashes in
`main_v1/config/frozen_source_hashes.sha256` remain unchanged.
