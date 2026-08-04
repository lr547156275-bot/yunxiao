# BOP-QB-PRT v1

The prerelease audit classifies the residual experiments as
`POST_RELEASE_RESIDUAL_WORK`. Mode 19 therefore sends at most two tagged,
zero-payload telemetry probes from the first collective QP's host during the
compute interval. The probes use that QP's five tuple and fixed path, are
serialized through the normal device queues, and return the normal INT header.

The tag is simulator metadata and adds no wire bytes. Probe ACKs are handled
before ordinary ACK processing: they do not acknowledge sequence bytes, change
the live rate, or participate in collective completion. Only ACKs received
before the earliest group release are eligible.

With two samples, PRT extrapolates a nonnegative queue slope to release. With
one sample it adds the capacity-times-age uncertainty margin. With no valid
sample it uses the unmodified BOP-QB queue observation. The estimate is clamped
to the frozen `0.5 * ECN` target and is used only in the existing group-credit
calculation. Base BOP planning, phase stagger, global barrier, QP identity,
sequence space, and mode 15 are unchanged.
