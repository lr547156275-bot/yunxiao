# Build and static-check report

- Build command: `cd simulation && python2 ./waf build`
- Result: **PASS**
- Final incremental build after the zero-rate overflow guard: 5.918 seconds
- ns-3 runs executed by this task: **0**

Static checks:

| Check | Result |
|---|---|
| `test_v20_model.py` | PASS, 3 tests |
| `test_v20_static.py` | PASS, 8 tests |
| Python `py_compile` | PASS |
| `bash -n` on v2.0 scripts | PASS |
| Manifest regeneration determinism | PASS |
| Prepared-run input/config/meta check | PASS |

`git diff --check` also reports trailing whitespace in historical, already-dirty sections of `simulation/scratch/third.cc`. These lines are outside the v2.0 additions and were not mechanically rewritten because they are shared user changes. This does not affect compilation.
