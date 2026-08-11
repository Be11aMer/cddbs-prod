"""
Social Media Analysis Pipeline

Handles Twitter and Telegram account analysis by:
1. Fetching data from platform APIs
2. Normalizing via adapters (TwitterAdapter / TelegramAdapter)
3. Building a prompt for Gemini analysis
4. Returning structured 7-section briefing
"""

import json
import re
from datetime import datetime, UTC

import httpx

from src.cddbs.config import settings
from src.cddbs.adapters import TwitterAdapter, TelegramAdapter, BriefingInput
from src.cddbs.pipeline.prompt_templates import get_social_media_prompt
from src.cddbs.utils.genai_client import call_gemini, is_gemini_error
from src.cddbs.utils.input_sanitizer import sanitize_text
from src.cddbs.database import SessionLocal
from src.cddbs import models
from src.cddbs.quality import score_briefing
from src.cddbs.narratives import match_narratives_from_report


def _format_briefing_input(briefing_input: BriefingInput) -> tuple[str, str]:
    """Convert normalized BriefingInput to text strings for the prompt."""
    # Bio, display name and post text are attacker-controlled account content
    # interpolated into the Gemini prompt — sanitise to defend against embedded
    # prompt injection (OWASP LLM01). Length caps mirror the analysis pipeline.
    profile = briefing_input.profile
    profile_lines = [
        f"Handle: {profile.handle}",
        f"Platform: {profile.platform}",
        f"Display Name: {sanitize_text(profile.display_name or '', 200)}",
        f"Bio: {sanitize_text(profile.bio or '', 2000)}",
        f"Followers: {profile.followers}",
        f"Following: {profile.following}",
        f"Total Posts: {profile.total_posts}",
        f"Created: {profile.created_at}",
        f"Language: {profile.language}",
        f"Verified: {profile.verified}",
    ]
    for k, v in profile.platform_metadata.items():
        profile_lines.append(f"{k}: {v}")
    profile_data = "\n".join(profile_lines)

    posts_lines = []
    for i, post in enumerate(briefing_input.posts[:50], 1):
        posts_lines.append(f"--- Post {i} ---")
        posts_lines.append("[BEGIN UNTRUSTED POST DATA]")
        posts_lines.append(f"ID: {post.post_id}")
        posts_lines.append(f"Text: {sanitize_text(post.text or '', 2000)}")
        posts_lines.append(f"Time: {post.timestamp}")
        posts_lines.append(f"Type: {post.media_type}")
        if post.engagement:
            eng = ", ".join(f"{k}: {v}" for k, v in post.engagement.items())
            posts_lines.append(f"Engagement: {eng}")
        if post.is_amplification:
            posts_lines.append(f"Amplified from: {post.amplification_source}")
        if post.urls:
            posts_lines.append(f"URLs: {', '.join(post.urls)}")
        if post.mentions:
            posts_lines.append(f"Mentions: {', '.join(post.mentions)}")
        posts_lines.append("[END UNTRUSTED POST DATA]")
        posts_lines.append("")

    posts_data = "\n".join(posts_lines) if posts_lines else "No posts available."
    return profile_data, posts_data


X_API_BASE = "https://api.x.com/2"


class XAPIError(RuntimeError):
    """An X API call failed in a way the operator needs to act on."""


def _raise_for_x_api(resp: httpx.Response, context: str) -> None:
    """Translate X API failures into messages that say what to do about them.

    X bills per read and returns 429 both for the short rate-limit window and
    for an exhausted monthly post cap, so a bare status code leaves the operator
    guessing which one they hit.
    """
    if resp.status_code == 200:
        return

    detail = ""
    try:
        body = resp.json()
        detail = body.get("detail") or body.get("title") or str(body)[:300]
    except Exception:
        detail = (resp.text or "")[:300]

    if resp.status_code == 401:
        raise XAPIError(
            f"{context}: X API rejected the credentials (401). "
            f"Check TWITTER_BEARER_TOKEN is a valid app Bearer token. {detail}"
        )
    if resp.status_code == 403:
        raise XAPIError(
            f"{context}: X API forbade the request (403). The project's access "
            f"tier likely does not include this endpoint. {detail}"
        )
    if resp.status_code == 429:
        reset = resp.headers.get("x-rate-limit-reset", "")
        remaining = resp.headers.get("x-user-limit-24hour-remaining", "")
        raise XAPIError(
            f"{context}: X API rate limit or monthly post cap hit (429). "
            f"reset={reset or 'unknown'} 24h_remaining={remaining or 'unknown'}. {detail}"
        )
    if resp.status_code == 404:
        raise XAPIError(f"{context}: not found (404). {detail}")

    raise XAPIError(f"{context}: X API returned {resp.status_code}. {detail}")


async def fetch_twitter_data(handle: str, max_posts: int | None = None) -> dict:
    """Fetch an X account profile and recent posts via X API v2.

    Uses the public read endpoints (user lookup + user posts timeline), which
    work for any public account. Requests the `referenced_tweets` expansions so
    retweet/quote sources can be attributed — without them the API returns only
    a bare reference ID and amplification analysis is impossible.
    """
    bearer = settings.TWITTER_BEARER_TOKEN
    if not bearer:
        raise ValueError("TWITTER_BEARER_TOKEN not configured")

    if max_posts is None:
        max_posts = settings.X_MAX_POSTS

    clean_handle = handle.lstrip("@")
    headers = {"Authorization": f"Bearer {bearer}"}

    async with httpx.AsyncClient(timeout=30) as client:
        # Get user profile
        user_resp = await client.get(
            f"{X_API_BASE}/users/by/username/{clean_handle}",
            headers=headers,
            params={
                "user.fields": "created_at,description,public_metrics,verified,verified_type,profile_image_url"
            },
        )
        _raise_for_x_api(user_resp, f"user lookup for @{clean_handle}")
        user_data = user_resp.json().get("data", {})
        user_id = user_data.get("id")

        if not user_id:
            raise ValueError(f"X user @{clean_handle} not found")

        # Get recent posts. max_results must be 5-100 per the API.
        tweets_resp = await client.get(
            f"{X_API_BASE}/users/{user_id}/tweets",
            headers=headers,
            params={
                "max_results": max(5, min(max_posts, 100)),
                "tweet.fields": "created_at,public_metrics,entities,referenced_tweets,lang,attachments",
                # Resolves referenced_tweets ({type,id}) to an author handle:
                # referenced_tweets.id -> includes.tweets[].author_id
                # referenced_tweets.id.author_id -> includes.users[].username
                "expansions": "referenced_tweets.id,referenced_tweets.id.author_id",
                "user.fields": "username",
            },
        )
        _raise_for_x_api(tweets_resp, f"posts timeline for @{clean_handle}")
        tweets_body = tweets_resp.json()
        tweets = tweets_body.get("data", [])

    return {
        "profile": user_data,
        "posts": tweets,
        # Side-loaded objects for the expansions above; TwitterAdapter indexes
        # these in build_context() to attribute amplification.
        "includes": tweets_body.get("includes", {}),
        "data_source": "x_api_v2",
        "collection_period": {
            "end": datetime.now(UTC).isoformat(),
        },
    }


async def fetch_telegram_data(channel: str) -> dict:
    """Fetch Telegram channel info and recent messages via Bot API."""
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN not configured")

    clean_channel = channel.lstrip("@")
    base_url = f"https://api.telegram.org/bot{bot_token}"

    async with httpx.AsyncClient(timeout=30) as client:
        # Get chat info
        chat_resp = await client.get(
            f"{base_url}/getChat",
            params={"chat_id": f"@{clean_channel}"},
        )
        chat_resp.raise_for_status()
        chat_data = chat_resp.json().get("result", {})

        # Get member count
        count_resp = await client.get(
            f"{base_url}/getChatMemberCount",
            params={"chat_id": f"@{clean_channel}"},
        )
        if count_resp.status_code == 200:
            chat_data["members_count"] = count_resp.json().get("result", 0)

    # Note: Bot API cannot fetch channel message history without admin access.
    # For production, this would need MTProto (Telethon/Pyrogram) or admin bot.
    return {
        "profile": chat_data,
        "posts": [],
        "data_source": "telegram_bot_api",
        "collection_period": {
            "end": datetime.now(UTC).isoformat(),
        },
    }


def run_social_media_pipeline(
    platform: str,
    handle: str,
    report_id: int | None = None,
    google_api_key: str | None = None,
    raw_data: dict | None = None,
) -> dict:
    """Run the social media analysis pipeline.

    Args:
        platform: "twitter" or "telegram"
        handle: Account handle (e.g., @rt_com or @rt_english)
        report_id: Optional existing report ID to update
        google_api_key: Optional Gemini API key override
        raw_data: Optional pre-fetched platform data (skips API fetch)
    """
    # Select adapter
    if platform == "twitter":
        adapter = TwitterAdapter()
    elif platform == "telegram":
        adapter = TelegramAdapter()
    else:
        raise ValueError(f"Unsupported platform: {platform}")

    # If no raw data provided, we need API keys
    if raw_data is None:
        raise ValueError(
            f"No data provided for {platform} analysis. "
            f"Set API keys ({platform.upper()}_BEARER_TOKEN / TELEGRAM_BOT_TOKEN) "
            f"and use the async fetch endpoint, or provide raw_data."
        )

    # Normalize data via adapter
    briefing_input = adapter.normalize(raw_data)
    profile_data, posts_data = _format_briefing_input(briefing_input)

    # Build prompt
    prompt = get_social_media_prompt(platform, handle, profile_data, posts_data)

    # Call Gemini
    raw_response = call_gemini(prompt, api_key=google_api_key)

    # --- Gemini failure detection (C-3, same defect as orchestrator.py) ---
    # call_gemini() returns a sentinel string instead of raising, so without this
    # the error text was stored as `final_report` with status "completed".
    if is_gemini_error(raw_response):
        session = SessionLocal()
        try:
            report = None
            if report_id:
                report = session.query(models.Report).filter(
                    models.Report.id == report_id
                ).first()
            if not report:
                report = models.Report(outlet=handle, country="")
                session.add(report)
                session.flush()

            report.analysis_status = "failed"
            report.final_report = None
            report.raw_response = raw_response
            report.data = {
                "platform": platform,
                "handle": handle,
                "articles_analyzed": len(briefing_input.posts),
                "status": "failed",
                "analysis_status": "failed",
                "analysis_date": datetime.now(UTC).isoformat(),
                "error": raw_response,
            }
            session.commit()
            session.refresh(report)
            return {
                "report_id": report.id,
                "platform": platform,
                "handle": handle,
                "final_report": None,
                "raw_response": raw_response,
                "structured_briefing": None,
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Parse JSON from response
    try:
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
        if json_match:
            clean_response = json_match.group(1).strip()
        else:
            json_match = re.search(r'(\{.*\})', raw_response, re.DOTALL)
            clean_response = json_match.group(1).strip() if json_match else raw_response.strip()
        payload = json.loads(clean_response)
    except Exception:
        payload = {"individual_analyses": [], "final_briefing": raw_response}

    final_report = payload.get("final_briefing", raw_response)

    # Persist to database
    session = SessionLocal()
    try:
        report = None
        if report_id:
            report = session.query(models.Report).filter(models.Report.id == report_id).first()

        if not report:
            report = models.Report(
                outlet=handle,
                country="",
            )
            session.add(report)
            session.flush()

        report.analysis_status = "completed"
        report.final_report = final_report
        report.raw_response = raw_response
        report.data = {
            "platform": platform,
            "handle": handle,
            "articles_analyzed": len(briefing_input.posts),
            "parsing_successful": "structured_briefing" in payload,
            "status": "completed",
            "analysis_status": "completed",
            "analysis_date": datetime.now(UTC).isoformat(),
            "structured_briefing": payload.get("structured_briefing"),
        }

        # Quality scoring
        try:
            quality_scorecard = score_briefing(payload)
            briefing = models.Briefing(
                report_id=report.id,
                briefing_json=payload,
                quality_score=quality_scorecard["total_score"],
                quality_rating=quality_scorecard["rating"],
                quality_details=quality_scorecard,
                prompt_version="v1.3",
            )
            session.add(briefing)
        except Exception as e:
            print(f"Quality scoring failed (non-fatal): {e}")

        # Narrative matching
        try:
            narrative_matches = match_narratives_from_report(
                report_text=final_report or raw_response,
                articles=[],
            )
            for nm in narrative_matches:
                session.add(models.NarrativeMatch(
                    report_id=report.id,
                    narrative_id=nm["narrative_id"],
                    narrative_name=nm["narrative_name"],
                    category=nm.get("category", ""),
                    confidence=nm.get("confidence", "low"),
                    matched_keywords=nm.get("matched_keywords", []),
                    match_count=nm.get("match_count", 0),
                ))
        except Exception as e:
            print(f"Narrative matching failed (non-fatal): {e}")

        session.commit()
        session.refresh(report)

        return {
            "report_id": report.id,
            "platform": platform,
            "handle": handle,
            "final_report": final_report,
            "raw_response": raw_response,
            "structured_briefing": payload.get("structured_briefing"),
        }
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
