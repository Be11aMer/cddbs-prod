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
from src.cddbs.utils.genai_client import call_gemini
from src.cddbs.database import SessionLocal
from src.cddbs import models
from src.cddbs.quality import score_briefing
from src.cddbs.narratives import match_narratives_from_report


def _format_briefing_input(briefing_input: BriefingInput) -> tuple[str, str]:
    """Convert normalized BriefingInput to text strings for the prompt."""
    profile = briefing_input.profile
    profile_lines = [
        f"Handle: {profile.handle}",
        f"Platform: {profile.platform}",
        f"Display Name: {profile.display_name}",
        f"Bio: {profile.bio}",
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
        posts_lines.append(f"ID: {post.post_id}")
        posts_lines.append(f"Text: {post.text}")
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
        posts_lines.append("")

    posts_data = "\n".join(posts_lines) if posts_lines else "No posts available."
    return profile_data, posts_data


async def fetch_twitter_data(handle: str) -> dict:
    """Fetch Twitter user profile and recent tweets via Twitter API v2."""
    bearer = settings.TWITTER_BEARER_TOKEN
    if not bearer:
        raise ValueError("TWITTER_BEARER_TOKEN not configured")

    clean_handle = handle.lstrip("@")
    headers = {"Authorization": f"Bearer {bearer}"}

    async with httpx.AsyncClient(timeout=30) as client:
        # Get user profile
        user_resp = await client.get(
            f"https://api.twitter.com/2/users/by/username/{clean_handle}",
            headers=headers,
            params={
                "user.fields": "created_at,description,public_metrics,verified,profile_image_url"
            },
        )
        user_resp.raise_for_status()
        user_data = user_resp.json().get("data", {})
        user_id = user_data.get("id")

        if not user_id:
            raise ValueError(f"Twitter user @{clean_handle} not found")

        # Get recent tweets
        tweets_resp = await client.get(
            f"https://api.twitter.com/2/users/{user_id}/tweets",
            headers=headers,
            params={
                "max_results": 50,
                "tweet.fields": "created_at,public_metrics,entities,referenced_tweets,lang,attachments",
            },
        )
        tweets_resp.raise_for_status()
        tweets = tweets_resp.json().get("data", [])

    return {
        "profile": user_data,
        "posts": tweets,
        "data_source": "twitter_api_v2",
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

        report.final_report = final_report
        report.raw_response = raw_response
        report.data = {
            "platform": platform,
            "handle": handle,
            "articles_analyzed": len(briefing_input.posts),
            "parsing_successful": "structured_briefing" in payload,
            "status": "completed",
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
