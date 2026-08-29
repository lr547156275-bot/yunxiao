set -u
cd /work/simulation/experiment/scheme1_sba
echo "=== 1. columns available in final_results.csv ==="
head -1 final_report/final_results.csv | tr ',' '\n' | nl | head -70
echo
echo "=== 2. is there a FINAL-FREEZE migration-off ablation? ==="
ls -d m_*migoff*_out m_*mig_off*_out 2>/dev/null || echo "  no migration-off output dirs"
ls s*_config_mig.txt 2>/dev/null | sed 's/^/  found config: /' || echo "  no *_config_mig.txt"
grep -l "CBAP_MIGRATION_ENABLE 0" m_cbapsba_s*_seed2.txt 2>/dev/null | sed 's/^/  mig=0 cell: /' || echo "  no cbapsba cell with migration disabled"
