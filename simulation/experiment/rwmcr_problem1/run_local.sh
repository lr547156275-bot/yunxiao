#!/usr/bin/env bash
set -eu

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
simulation_dir="$(CDPATH= cd -- "${script_dir}/../.." && pwd)"
cd "${simulation_dir}"

mkdir -p experiment/rwmcr_problem1/results
python2 ./waf build -j"$(nproc)"
python2 ./waf --targets=third --run "scratch/third experiment/rwmcr_problem1/config_collision.txt" \
  > experiment/rwmcr_problem1/results/run_collision.log 2>&1
python2 ./waf --targets=third --run "scratch/third experiment/rwmcr_problem1/config_oracle.txt" \
  > experiment/rwmcr_problem1/results/run_oracle.log 2>&1
