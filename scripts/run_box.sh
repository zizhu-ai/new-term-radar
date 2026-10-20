#!/bin/bash
# usage: scripts/run_box.sh sources|daily   (X posts: shared pull → out/x_posts-*.json)
# Prefers X_POSTS_GLOB (merge shards ≤ LOOKBACK_HOURS); falls back to today's single file.
cd /workspace/new-term-radar || exit 1
EXTRA="${@:2}"
export LLM_API_KEY="${LLM_API_KEY:-$MIMO_API_KEY}" LLM_MODEL="${LLM_MODEL:-mimo-v2.6-pro}"
if [ -z "${GOANYAPI_API_KEY:-}" ] && [ -f "$HOME/.config/goanyapi-token" ]; then
  export GOANYAPI_API_KEY="$(cat "$HOME/.config/goanyapi-token")"
fi
D=$(date +%F)
export X_POSTS_GLOB="${X_POSTS_GLOB:-out/x_posts-*.json}"
# Keep X_POSTS_FILE for older callers / single-file days
X="out/x_posts-$D.json"
[ -f "$X" ] && export X_POSTS_FILE="${X_POSTS_FILE:-$X}"
N="out/columbus_newsites-$D.json"
[ -f "$N" ] && export NEW_SITES_FILE="${NEW_SITES_FILE:-$N}"
mkdir -p out
if [ "$1" = sources ]; then
  python3 -m radar sources --out "out/sources-$D-$(date +%H%M).md"
else
  python3 -m radar daily --skip x,hf $EXTRA --out "out/daily-$D.md"
fi
