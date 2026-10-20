"""Convert x-MCP get_users_posts dumps into the AIsa get_twitter_user_last_tweets shape.
usage: python3 scripts/x_mcp_to_aisa.py out.json handle=file [handle=file ...]"""
import json, sys
from datetime import datetime
out = {}
for arg in sys.argv[2:]:
    h, f = arg.split("=", 1)
    t = open(f).read()
    try:
        j = json.loads(t[t.index("{"):t.rindex("}") + 1])
    except ValueError:
        continue
    tweets = []
    for p in j.get("data") or []:
        ts = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00"))
        tweets.append({"text": p.get("text", ""), "likeCount": (p.get("public_metrics") or {}).get("like_count", 0),
                       "url": p.get("url") or f"https://x.com/{h}/status/{p['id']}",
                       "createdAt": ts.strftime("%a %b %d %H:%M:%S %z %Y")})
    out[h] = {"data": {"tweets": tweets}}
json.dump(out, open(sys.argv[1], "w"), ensure_ascii=False)
print(len(out), "accounts,", sum(len(v["data"]["tweets"]) for v in out.values()), "posts")
