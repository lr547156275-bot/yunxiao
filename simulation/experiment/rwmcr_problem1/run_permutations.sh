#!/usr/bin/env bash
set -eu

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
simulation_dir="$(CDPATH= cd -- "${script_dir}/../.." && pwd)"
cd "${simulation_dir}"

python2 ./waf build -j"$(nproc)"

validate_run() {
  permutation="$1"
  scheme="$2"
  expected="$3"
  result_dir="experiment/rwmcr_problem1/results/permutation_${permutation}"
  fct_file="${result_dir}/fct_${scheme}.txt"
  path_file="${result_dir}/path_${scheme}.log"
  port_file="${result_dir}/port_${scheme}.txt"
  queue_file="${result_dir}/queue_${scheme}.txt"
  log_file="${result_dir}/run_${scheme}.log"

  test "$(wc -l < "${fct_file}")" -eq 8
  test "$(tail -n +2 "${path_file}" | wc -l)" -eq 8
  actual="$(awk 'NR>1 {c[$7]++} END {printf "%d:%d:%d:%d",c[18]+0,c[19]+0,c[20]+0,c[21]+0}' "${path_file}")"
  test "${actual}" = "${expected}"
  test "$(awk '{seen[$1 FS $2 FS $3 FS $4]++} END {print length(seen)}' "${fct_file}")" -eq 8
  if grep -Eiq 'assert|aborted|segmentation|FIXED_PATH_ERROR|Build failed|runtime error|drop' "${log_file}"; then
    echo "error marker found in ${log_file}" >&2
    return 1
  fi
  awk 'NR==1 {print "time_ns node_id peer_id if_index queue_bytes"; next} {print $1,$2,$3,$4,$7}' "${port_file}" > "${queue_file}"
  echo "P${permutation} ${scheme} OK paths=${actual} fct=8"
}

for permutation in 0 1 2 3 4; do
  result_dir="experiment/rwmcr_problem1/results/permutation_${permutation}"
  mkdir -p "${result_dir}"
  for scheme in collision oracle; do
    config="experiment/rwmcr_problem1/permutations/permutation_${permutation}/config_${scheme}.txt"
    log="${result_dir}/run_${scheme}.log"
    python2 ./waf --targets=third --run "scratch/third ${config}" > "${log}" 2>&1
    if test "${scheme}" = collision; then
      validate_run "${permutation}" "${scheme}" "5:2:1:0"
    else
      validate_run "${permutation}" "${scheme}" "2:2:2:2"
    fi
  done
done
