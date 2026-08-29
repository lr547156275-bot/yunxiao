cd /work/simulation/experiment/scheme1_sba
echo "=== (5.5/5.6) dynamic PFC threshold during the batch, per rho ==="
for t in 055 075 090 09875; do
  n=au_s3_rho$t
  f=${n}_out/pfc_audit.csv
  [ -f "$f" ] || { echo "  $n: NO AUDIT FILE"; continue; }
  echo "--- $n  ($(wc -l < $f) rows)"
  awk -F, 'NR>1 && $1>=2000000000 && $1<=2090000000 {
      th=$7; occ=$6; sl=$8; q=$3; su=$10;
      n++;
      if(n==1||th<thmin)thmin=th; if(n==1||th>thmax)thmax=th; thsum+=th;
      if(n==1||occ>occmax)occmax=occ;
      if(n==1||sl<slmin)slmin=sl;
      if(n==1||q>qmax)qmax=q;
      if(n==1||su>sumax)sumax=su;
      st[$14]++
    } END{
      printf "  thresh  min=%d mean=%.0f max=%d  (%.2f/%.2f/%.2f us)\n", thmin, thsum/n, thmax, thmin*8/10e9*1e6, thsum/n*8/10e9*1e6, thmax*8/10e9*1e6;
      printf "  pfc_occ max=%d B (%.2f us)   slack min=%d B\n", occmax, occmax*8/10e9*1e6, slmin;
      printf "  cbap egress q max=%d B (%.2f us)   shared_used max=%d B\n", qmax, qmax*8/10e9*1e6, sumax;
      printf "  guard states:"; for(s in st) printf " %s=%d", s, st[s]; printf "\n  rows=%d\n", n
    }' "$f"
done
echo
echo "=== ratio check: is PFC occupancy even comparable to egress queue? ==="
awk -F, 'NR>1 && $1>=2000000000 && $1<=2090000000 && $3>0 {c++; s+=$6/$3} END{printf "  mean(pfc_occ / egress_q) = %.4f over %d samples\n", s/c, c}' au_s3_rho09875_out/pfc_audit.csv
