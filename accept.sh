set -u
cd /work/simulation/experiment/scheme1_sba
echo "############ S4 eta_feasibility trace ############"
column -s, -t g_cbapsba_s4_seed2_out/eta_feasibility.csv | cut -c1-186
echo
echo "############ trace-internal checks (both cells) ############"
for tag in s3 s4; do
  printf "  %s: " "$tag"
  awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next}
  { n++
    eb=$(h["eta_base"])+0; ef=$(h["eta_feasible"])+0; ee=$(h["eta_effective"])+0
    w=(ef>eb?ef:eb); if(w>1)w=1
    if ((ee-w)>1e-6 || (w-ee)>1e-6) be++
    if ($(h["final_sum_target_bps"])+0 > $(h["link_capacity_bps"])+0) bc++
    if ($(h["feasible"])+0 != 1) nf++
    if (ee>eb+1e-9) raised++
  }
  END{printf "rows=%d  identity=%s  capacity=%s  feasible=%s  eta_raised_in=%d rows\n",
      n, (be?"FAIL("be")":"PASS"), (bc?"FAIL("bc")":"PASS"), (nf?"FAIL("nf")":"PASS"), raised+0}' \
  g_cbapsba_${tag}_seed2_out/eta_feasibility.csv
done
