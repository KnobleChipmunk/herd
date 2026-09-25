#!/usr/bin/env bash
# usage: watch_review.sh <worktree> <id>   — exits when the review is clean, capped, or after ~55 min
shopt -s nullglob
W="$1"; ID="$2"
for i in $(seq 1 110); do
  files=("$W"/REVIEW-"$ID"-round-*.md)
  if (( ${#files[@]} )) && grep -lq "REVIEW CLEAN" "${files[@]}"; then echo "CLEAN: ${files[-1]}"; exit 0; fi
  if [[ -f "$W/REVIEW-$ID-round-2.md" ]] && grep -q "^FINDINGS" "$W/REVIEW-$ID-round-2.md"; then echo "ROUND 2 HAS FINDINGS (cap)"; exit 0; fi
  sleep 30
done
echo "TIMEOUT: $(ls "$W" | grep -i 'HANDOFF\|REVIEW' | tr '\n' ' ')"
