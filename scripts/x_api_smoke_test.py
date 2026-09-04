#!/usr/bin/env python3
"""Live smoke test for the X (Twitter) collection path.

Everything in tests/test_x_api_integration.py runs against a mocked HTTP
transport, so it proves the code's logic but not that X actually accepts our
credentials or returns the shape we expect. This script makes the real calls.

X bills per read under pay-per-use, so it runs in two stages and stops at the
first failure:

  Stage 1  user lookup only   ~1 user read
           Proves the Bearer token authenticates and the account is funded.
  Stage 2  posts timeline     ~N post reads (N = --max-posts, default 10)
           Proves the referenced_tweets expansions come back and that
           amplification sources actually resolve to handles.

Stage 1 alone answers "is my token good and are my credits live?", so start
there before spending anything on a timeline.

Usage:
    export TWITTER_BEARER_TOKEN='AAAA...'
    python scripts/x_api_smoke_test.py                    # stage 1 only
    python scripts/x_api_smoke_test.py --with-timeline    # stages 1 and 2
    python scripts/x_api_smoke_test.py --with-timeline --handle @rt_com --max-posts 10

Nothing is written to the database and no Gemini call is made.
"""
import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
)
# httpx logs every request at INFO; keep the output focused on our own lines.
logging.getLogger("httpx").setLevel(logging.WARNING)


def _rule(title):
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handle", default="@rt_com", help="Account to probe")
    parser.add_argument(
        "--with-timeline",
        action="store_true",
        help="Also fetch the posts timeline (costs post reads)",
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=10,
        help="Posts to fetch in stage 2 (clamped by the API to 5-100)",
    )
    args = parser.parse_args()

    if not os.getenv("TWITTER_BEARER_TOKEN"):
        print("TWITTER_BEARER_TOKEN is not set in this shell.")
        print("Run:  export TWITTER_BEARER_TOKEN='AAAA...'")
        return 2

    from src.cddbs.adapters import TwitterAdapter
    from src.cddbs.pipeline import social_media_pipeline as smp

    token = smp.settings.TWITTER_BEARER_TOKEN
    print(f"Token loaded: {len(token)} chars, starts {token[:6]!r}")
    print(f"Endpoint base: {smp.X_API_BASE}")
    print(f"X_MAX_POSTS default: {smp.settings.X_MAX_POSTS}")

    # ------------------------------------------------------------------
    # Stage 1 — user lookup. One user read.
    # ------------------------------------------------------------------
    _rule("STAGE 1 — user lookup (auth + funding check)")
    handle = args.handle.lstrip("@")
    import httpx

    try:
        resp = httpx.get(
            f"{smp.X_API_BASE}/users/by/username/{handle}",
            headers={"Authorization": f"Bearer {token}"},
            params={"user.fields": "created_at,description,public_metrics,verified"},
            timeout=30,
        )
        smp._raise_for_x_api(resp, f"user lookup for @{handle}")
    except smp.XAPIError as exc:
        print(f"\nRESULT: STAGE 1 FAILED\n{exc}")
        return 1
    except Exception as exc:
        print(f"\nRESULT: STAGE 1 ERRORED (network/transport)\n{type(exc).__name__}: {exc}")
        return 1

    profile = resp.json().get("data", {})
    print("\nRESULT: STAGE 1 PASSED — credentials valid and account funded.")
    print(f"  handle    : @{profile.get('username')}")
    print(f"  name      : {profile.get('name')}")
    print(f"  followers : {profile.get('public_metrics', {}).get('followers_count')}")

    if not args.with_timeline:
        print("\nStopping before the timeline. Re-run with --with-timeline to")
        print("verify amplification attribution (costs post reads).")
        return 0

    # ------------------------------------------------------------------
    # Stage 2 — timeline with expansions. N post reads.
    # ------------------------------------------------------------------
    _rule(f"STAGE 2 — posts timeline ({args.max_posts} posts)")
    try:
        raw = asyncio.run(
            smp.fetch_twitter_data(args.handle, max_posts=args.max_posts)
        )
    except smp.XAPIError as exc:
        print(f"\nRESULT: STAGE 2 FAILED\n{exc}")
        return 1
    except Exception as exc:
        print(f"\nRESULT: STAGE 2 ERRORED\n{type(exc).__name__}: {exc}")
        return 1

    posts = raw.get("posts", [])
    includes = raw.get("includes", {}) or {}
    print(f"\nposts returned      : {len(posts)}")
    print(f"includes.tweets     : {len(includes.get('tweets', []))}")
    print(f"includes.users      : {len(includes.get('users', []))}")

    if not includes:
        print("\nWARNING: `includes` came back empty. Either none of these posts")
        print("are retweets/quotes, or the expansions were not honoured.")

    briefing = TwitterAdapter().normalize(raw)
    amplified = [p for p in briefing.posts if p.is_amplification]
    attributed = [p for p in amplified if p.amplification_source]

    print(f"\namplification posts : {len(amplified)} of {len(briefing.posts)}")
    print(f"with source handle  : {len(attributed)}")

    for post in amplified[:5]:
        source = post.amplification_source or "(UNRESOLVED)"
        print(f"  - {post.post_id}: source={source}")

    _rule("VERDICT")
    if not amplified:
        print("INCONCLUSIVE — no retweets or quotes in this sample, so")
        print("amplification attribution could not be exercised.")
        print("Try a larger --max-posts or an account that retweets more.")
        return 0
    if attributed:
        print(f"PASSED — {len(attributed)}/{len(amplified)} amplification posts")
        print("resolved to a source handle. The expansions fix works.")
        return 0
    print(f"FAILED — {len(amplified)} amplification posts found but NONE")
    print("resolved to a handle. The expansions are not coming back as expected.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
