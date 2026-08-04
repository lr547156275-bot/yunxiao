RATEFLOOR_SEMANTIC_PASS

# Rate-floor semantic validation

Expected/reused runs: 5/5.
Failures: 0.

Hard checks include exact positive grants, zero-grant pause/resume, sender packet gaps, scope delay, and post-application capacity. Tail packets use their actual smaller wire size; every packet is checked against the exact ceil(bits/rate) formula.

## Failures

- None.
