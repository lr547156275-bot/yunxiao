set -u
P=/work/matrix_logs/pre_freeze_run
# Measured: a parallel pair costs ~1.50x one cell's serial time, so a pair of
# equal cells finishes in 1.50x instead of 2.00x -> speedup 1.33x.
# Each scenario runs 2 pairs + 1 solo cell (5 algorithms, odd count).
awk 'BEGIN{
  split("s1 s2 s3 s6 s4 s5", T, " ")
  printf "  %-4s %-11s %-13s %-13s %s\n", "scen", "serial_min", "parallel_min", "saving", "shape"
  tot_s=0; tot_p=0
}
{ w[$1"_"$2]=$3 }
END{
  split("s1 s2 s3 s6 s4 s5", T, " ")
  split("dcqcn dctcp timely hpcc cbapsba", A, " ")
  for (i=1;i<=6;i++){
    t=T[i]; s=0; n=0; mx=0
    for (j=1;j<=5;j++){ v=w[A[j]"_"t]+0; if(v>0){ s+=v; n++; if(v>mx)mx=v } }
    if (n<5) continue
    avg = s/n
    # 2 pairs at 1.50*avg each, plus 1 solo at avg
    par = 2*(1.50*avg) + avg
    tot_s += s; tot_p += par
    printf "  %-4s %-11.0f %-13.0f %-13.0f 2 pairs + 1 solo\n", t, s/60, par/60, (s-par)/60
  }
  printf "\n  TOTAL serial   = %.1f h\n", tot_s/3600
  printf "  TOTAL parallel = %.1f h   (speedup %.2fx, saves %.1f h)\n", tot_p/3600, tot_s/tot_p, (tot_s-tot_p)/3600
}' <(for t in s1 s2 s3 s6 s4 s5; do for a in dcqcn dctcp timely hpcc cbapsba; do
  f=$P/m_${a}_${t}_seed2.manifest
  [ -f "$f" ] && echo "$a $t $(awk -F= '$1=="wall_seconds"{print $2}' $f)"
done; done)
