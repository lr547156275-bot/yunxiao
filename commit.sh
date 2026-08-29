set -u
cd /workspaces/yunxiao
git -c user.name="bshu02" -c user.email="bshu02@ubiq2.com" commit -q -F - <<'MSG'
archive final CBAP-SBA freeze before motivation experiments

Snapshot of the completed evaluation before starting motivation experiments on a
separate branch. No algorithm code is changed by this commit.

Contents:
  * the FINAL FREEZE 30-cell matrix results (final_report/), replacing the
    pre-freeze report; the pre-freeze report and analysis_s*/ are preserved as
    *_pre_freeze/ so the before/after comparison stays available
  * paper_data/: 13 CSVs, paper_results_summary.md, paper_metadata.md,
    RESULTS_README.md, 32 manifests, trigger/safety tables, anomalies.md
  * the S3 migration-off ablation config (config-only change, no source edit)
  * per-cell configs for all 30 matrix cells and the eta sweep

Deliberately NOT committed: raw traces (qlen.txt, selected_*_timeseries.csv,
~4.3 GB). They exceed GitHub's file limit and regenerate from the committed
configs plus the pinned binaries. The 53 file deletions in this commit are
pre-freeze chart files superseded by the frozen report; all 53 remain
recoverable from 2ece98e.

Frozen build this data came from:
  third   0156d0bacf69034f78703fcff4a26cb37b976da8d17b8ca7c9c25e696c7f3d35
  p2p lib 0bacef18ef8547302f2f9b239951cb131f4efaa09f31fedbdf17889f8cd0ef72

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
echo "=== commit ==="
git log --oneline -1
git rev-parse HEAD
