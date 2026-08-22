# ACTUATION PROVENANCE

## Item 2: rec2 vs ckpt4 -- NOT proven event-identical

| asset | rec2_s3_on_out | ckpt4_cbap_s3_out |
|---|---|---|
| binary sha256 | **265fe2a1a31d5e1809458c9e5b44120b528c2524ae2642cbd7185072a7b68103** | **290cb41fec981bc848cbfd518257ce2c5df1384d52f2325d67955acaabd880b7** |
| libns3 sha256 | c643f5cc332e02763946b01b8aa1cc17c50daf4dda53a371c13e4576525eb122 | c643f5cc332e02763946b01b8aa1cc17c50daf4dda53a371c13e4576525eb122 |
| third.cc sha256 | 84349f041424506b913072796bf2b224d59c4d82e6db679069c12dbd2f6802cd (at that build) | dd54dee455cbe9f7269186facc9a3ac688fb83785be7aab97bc95b29f57be831 |
| recorder-ml header | 4b9a4098a6d31625e46d24cfd371956cfb1a3bb9c98bbc327a7de332c0ce4b10 | 4b9a4098a6d31625e46d24cfd371956cfb1a3bb9c98bbc327a7de332c0ce4b10 |
| config sha256 | 8f30980b216dba81020de24ec5ec66ef019b411782d78900b80ccd075a3fe2b0 | 69dbc4159577fceb2edd7cc7d0a138c1d321cf94aff45d6256eab43c33410bbf |
| topology / flow / link / path | 6091d5ec / 6b922c67 / 70903775 / 1557487d (identical) | same |
| SIM_SEED | 2 | 2 |

**The binaries differ.**  `290cb41f` adds the `CBAP_REALLOC_PARSED` stdout echo
that `265fe2a1` lacks.  Per the instruction, "FCT strings identical" is NOT
sufficient to prove event-level trajectory identity.

Therefore **every actuation -> performance statement in this round is labelled
`CROSS_RUN_DIAGNOSTIC` and is not a causal result.**

The clean fix (not performed this round, as instructed): add only
`CBAP_ACTUATION_FILE` to the ckpt4 CBAP config, re-run S3 once under binary
`290cb41f`, and verify every core output byte-identical except the new log.
Estimated cost: ~18 min, ~120 MB.

## Inputs actually used

| purpose | file | sha256 |
|---|---|---|
| stage timestamps | rec2_s3_on_out/actuation.csv | 724d0f25416d4ed57c3ae3fa373005adf7e82f671e1c305fe7d8045022ba7047 |
| queue / zone / boost | ckpt4_cbap_s3_out/qc_trace.csv | 364bfe705d02ca3ccd75805da0244e2c4532b4720ae1cb02d0d98f6d3f6fb617 |
| served rate | ckpt4_cbap_s3_out/selected_link_timeseries.csv | b489c9fe46a7b4a347030ddca09a839895e66af3383e66e172ba026576a8bcda |

Window: W2 = [2.000000000, 2.058372997] s.  Sample interval 10 us (verified
uniform, n=5838, min=max=1.0e-5 s).
