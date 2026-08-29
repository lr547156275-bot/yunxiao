set -u
cd /workspaces/yunxiao
git merge --ff-only FETCH_HEAD 2>&1 | grep -E "^\s+simulation/|^\s+[a-z]" | tr -d '\t ' | grep -v '^$' > /tmp/blk.txt || true
n=$(wc -l < /tmp/blk.txt)
echo "  blockers: $n"
same=0; diff=0
while read -r f; do
  [ -f "$f" ] || continue
  a=$(sha256sum "$f" | cut -d' ' -f1)
  b=$(git show "FETCH_HEAD:$f" 2>/dev/null | sha256sum | cut -d' ' -f1)
  if [ "$a" = "$b" ]; then same=$((same+1)); else diff=$((diff+1)); echo "  DIFFERS: $f"; fi
done < /tmp/blk.txt
echo "  identical to incoming: $same   genuinely different: $diff"
if [ "$diff" -eq 0 ]; then
  while read -r f; do [ -f "$f" ] && rm -f "$f"; done < /tmp/blk.txt
  git merge --ff-only FETCH_HEAD 2>&1 | tail -1
  echo "  HEAD now: $(git rev-parse --short HEAD)"
else
  echo "  NOT removing anything -- real differences present"
fi
