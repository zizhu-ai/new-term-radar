#!/bin/bash
# usage: scripts/run_box.sh sources|daily   (X posts: shared pull → out/x_posts-*.json)
# Prefers X_POSTS_GLOB (merge shards ≤ LOOKBACK_HOURS); falls back to today's single file.
cd /workspace/new-term-radar || exit 1
EXTRA="${@:2}"
# Beijing calendar date for out/ filenames (digest day).
export TZ="${TZ:-Asia/Shanghai}"
# Durable MiMo key (paid sk- or Token Plan tp-/ttp-); Cursor injects MIMO_API_KEY into agent shells.
if [ -z "${MIMO_API_KEY:-}" ] && [ -f "$HOME/.config/mimo-api-key" ]; then
  export MIMO_API_KEY="$(cat "$HOME/.config/mimo-api-key")"
fi
export LLM_API_KEY="${LLM_API_KEY:-$MIMO_API_KEY}" LLM_MODEL="${LLM_MODEL:-mimo-v2.6-pro}"
# sk- → pay-as-you-go api.xiaomimimo.com; tp-/ttp- → Token Plan host
if [ -z "${LLM_BASE_URL:-}" ]; then
  case "${LLM_API_KEY:-}" in
    tp-*|ttp-*) export LLM_BASE_URL="https://token-plan-cn.xiaomimimo.com/v1" ;;
    *) export LLM_BASE_URL="https://api.xiaomimimo.com/v1" ;;
  esac
fi
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
# Unbuffered so logs show progress; hard cap whole run so a dead source can't hang forever.
export PYTHONUNBUFFERED=1
CAP="timeout -k 30 ${RADAR_RUN_TIMEOUT:-3600}"
STAMP=$(date +%H%M)
if [ "$1" = sources ]; then
  EXPECT="out/sources-$D-$STAMP.md"
  $CAP python3 -m radar sources --out "$EXPECT"
  rc=$?
else
  EXPECT="out/daily-$D.md"
  $CAP python3 -m radar daily --skip x,hf $EXTRA --out "$EXPECT"
  rc=$?
fi

# Fail loud if --out never landed (empty/missing): prevents "run ok, disk empty" gaps.
if [ -f "$EXPECT" ] && [ -s "$EXPECT" ]; then
  echo "durable ok: $EXPECT ($(wc -c < "$EXPECT") bytes)"
else
  echo "durable write verify FAILED for command=$1 date=$D out=$EXPECT rc=$rc" >&2
  exit 2
fi
exit "$rc"
