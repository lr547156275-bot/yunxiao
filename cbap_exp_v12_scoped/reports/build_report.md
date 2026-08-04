# Build report

- Command: `cd simulation && python2 ./waf build`
- Result: PASS
- Compiler/runtime: recorded in `preflight/toolchain.txt`
- Static tests: 11/11 PASS
- Python syntax checks: PASS
- Shell `bash -n`: PASS
- ns-3 experiments executed by this task: 0

The initial plain `./waf build` selected Python 3 and failed while parsing the
repository's Python-2-era wscript. This was a tool invocation mismatch, not a
C++ failure. Re-running with the repository-required `python2` completed the
incremental build successfully.
