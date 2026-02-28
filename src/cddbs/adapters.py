"""
CDDBS Platform Adapters

Normalizes platform-specific data (Twitter, Telegram) into a common
BriefingInput format for the LLM analysis pipeline.
Integrated from research Sprint 2-3.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PostData:
    """Normalized post/message data across platforms."""

    post_id: str
    text: str
    timestamp: datetime
    language: str = ""
    media_type: str = ""  # text, image, video, poll, document
    engagement: dict = field(default_factory=dict)
    is_amplification: bool = False  # retweet/forward
    amplification_source: str = ""
    urls: list = field(default_factory=list)
    mentions: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)


@dataclass
class ProfileData:
    """Normalized account/channel profile data."""

    handle: str
    platform: str
    display_name: str = ""
    bio: str = ""
    followers: int = 0
    following: int = 0
    total_posts: int = 0
    created_at: str = ""
    language: str = ""
    verified: bool = False
    platform_metadata: dict = field(default_factory=dict)


@dataclass
class BriefingInput:
    """Common input format for the CDDBS analysis pipeline."""

    profile: ProfileData
    posts: list = field(default_factory=list)  # List[PostData]
    collection_period: dict = field(default_factory=dict)  # {start, end}
    data_source: str = ""


class PlatformAdapter:
    """Abstract base for platform-specific data normalization."""

    platform: str = ""

    def normalize_profile(self, raw_profile: dict) -> ProfileData:
        raise NotImplementedError

    def normalize_post(self, raw_post: dict) -> PostData:
        raise NotImplementedError

    def normalize(self, raw_data: dict) -> BriefingInput:
        profile = self.normalize_profile(raw_data.get("profile", {}))
        posts = [
            self.normalize_post(p) for p in raw_data.get("posts", [])
        ]
        return BriefingInput(
            profile=profile,
            posts=posts,
            collection_period=raw_data.get("collection_period", {}),
            data_source=raw_data.get("data_source", f"{self.platform}_api"),
        )


class TwitterAdapter(PlatformAdapter):
    """Normalizes Twitter/X API v2 data into BriefingInput format."""

    platform = "twitter"

    def normalize_profile(self, raw_profile: dict) -> ProfileData:
        public_metrics = raw_profile.get("public_metrics", {})
        return ProfileData(
            handle=f"@{raw_profile.get('username', '')}",
            platform="twitter",
            display_name=raw_profile.get("name", ""),
            bio=raw_profile.get("description", ""),
            followers=public_metrics.get("followers_count", 0),
            following=public_metrics.get("following_count", 0),
            total_posts=public_metrics.get("tweet_count", 0),
            created_at=_parse_twitter_date(raw_profile.get("created_at", "")),
            language=raw_profile.get("lang", ""),
            verified=raw_profile.get("verified", False),
            platform_metadata={
                "twitter_is_blue_verified": raw_profile.get("is_blue_verified", False),
                "twitter_list_memberships": public_metrics.get("listed_count", 0),
            },
        )

    def normalize_post(self, raw_post: dict) -> PostData:
        public_metrics = raw_post.get("public_metrics", {})
        ref_tweets = raw_post.get("referenced_tweets", [])

        is_retweet = any(r.get("type") == "retweeted" for r in ref_tweets)
        is_quote = any(r.get("type") == "quoted" for r in ref_tweets)

        amplification_source = ""
        if is_retweet and ref_tweets:
            amplification_source = ref_tweets[0].get("author_username", "")

        urls = []
        for url_obj in raw_post.get("entities", {}).get("urls", []):
            urls.append(url_obj.get("expanded_url", url_obj.get("url", "")))

        mentions = []
        for m in raw_post.get("entities", {}).get("mentions", []):
            mentions.append(f"@{m.get('username', '')}")

        media_type = "text"
        attachments = raw_post.get("attachments", {})
        if attachments.get("media_keys"):
            media_type = "image"
        if raw_post.get("poll"):
            media_type = "poll"

        return PostData(
            post_id=raw_post.get("id", ""),
            text=raw_post.get("text", ""),
            timestamp=_parse_twitter_datetime(raw_post.get("created_at", "")),
            language=raw_post.get("lang", ""),
            media_type=media_type,
            engagement={
                "likes": public_metrics.get("like_count", 0),
                "retweets": public_metrics.get("retweet_count", 0),
                "replies": public_metrics.get("reply_count", 0),
                "quotes": public_metrics.get("quote_count", 0),
                "impressions": public_metrics.get("impression_count", 0),
            },
            is_amplification=is_retweet or is_quote,
            amplification_source=amplification_source,
            urls=urls,
            mentions=mentions,
            raw=raw_post,
        )


class TelegramAdapter(PlatformAdapter):
    """Normalizes Telegram MTProto/Bot API data into BriefingInput format."""

    platform = "telegram"

    def normalize_profile(self, raw_profile: dict) -> ProfileData:
        channel_type = raw_profile.get("type", "channel")
        subscriber_count = raw_profile.get("members_count", 0)
        return ProfileData(
            handle=f"@{raw_profile.get('username', '')}",
            platform="telegram",
            display_name=raw_profile.get("title", ""),
            bio=raw_profile.get("description", ""),
            followers=subscriber_count,
            following=0,
            total_posts=raw_profile.get("message_count", 0),
            created_at=_parse_telegram_date(raw_profile.get("date", "")),
            language=raw_profile.get("lang", ""),
            verified=raw_profile.get("verified", False),
            platform_metadata={
                "telegram_channel_type": channel_type,
                "telegram_subscriber_count": subscriber_count,
                "telegram_is_verified": raw_profile.get("verified", False),
                "telegram_linked_chat": raw_profile.get("linked_chat_username", ""),
                "telegram_invite_link": raw_profile.get("invite_link", ""),
            },
        )

    def normalize_post(self, raw_post: dict) -> PostData:
        is_forward = raw_post.get("forward_from_chat") is not None or \
                     raw_post.get("forward_from") is not None
        amplification_source = ""
        if is_forward:
            fwd_chat = raw_post.get("forward_from_chat", {})
            amplification_source = fwd_chat.get("username", "") or \
                                   fwd_chat.get("title", "unknown")

        urls = []
        for entity in raw_post.get("entities", []):
            if entity.get("type") == "url":
                offset = entity.get("offset", 0)
                length = entity.get("length", 0)
                text = raw_post.get("text", "")
                urls.append(text[offset:offset + length])
            elif entity.get("type") == "text_link":
                urls.append(entity.get("url", ""))

        mentions = []
        for entity in raw_post.get("entities", []):
            if entity.get("type") == "mention":
                offset = entity.get("offset", 0)
                length = entity.get("length", 0)
                text = raw_post.get("text", "")
                mentions.append(text[offset:offset + length])

        media_type = "text"
        if raw_post.get("photo"):
            media_type = "image"
        elif raw_post.get("video"):
            media_type = "video"
        elif raw_post.get("document"):
            media_type = "document"
        elif raw_post.get("poll"):
            media_type = "poll"
        elif raw_post.get("voice"):
            media_type = "voice"

        return PostData(
            post_id=str(raw_post.get("message_id", "")),
            text=raw_post.get("text", ""),
            timestamp=_parse_telegram_datetime(raw_post.get("date", "")),
            language="",
            media_type=media_type,
            engagement={
                "views": raw_post.get("views", 0),
                "forwards": raw_post.get("forwards", 0),
                "replies": raw_post.get("reply_count", 0),
            },
            is_amplification=is_forward,
            amplification_source=amplification_source,
            urls=urls,
            mentions=mentions,
            raw=raw_post,
        )


# --- Helper Functions ---

def _parse_twitter_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return ""


def _parse_twitter_datetime(date_str: str) -> datetime:
    if not date_str:
        return datetime.min
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return datetime.min


def _parse_telegram_date(date_val) -> str:
    if not date_val:
        return ""
    if isinstance(date_val, (int, float)):
        return datetime.utcfromtimestamp(date_val).strftime("%Y-%m-%d")
    if isinstance(date_val, str):
        try:
            dt = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return ""
    return ""


def _parse_telegram_datetime(date_val) -> datetime:
    if not date_val:
        return datetime.min
    if isinstance(date_val, (int, float)):
        return datetime.utcfromtimestamp(date_val)
    if isinstance(date_val, str):
        try:
            return datetime.fromisoformat(date_val.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return datetime.min
    return datetime.min
