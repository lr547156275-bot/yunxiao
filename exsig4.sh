cd /work/simulation
echo "=== is ShortGapPipeline defined anywhere? ==="
grep -rn "ShortGapPipeline" --include=*.h --include=*.cc . | head
echo
echo "=== context of line 2766 (is it inside #if 0 / a comment?) ==="
sed -n '2735,2775p' scratch/third.cc
