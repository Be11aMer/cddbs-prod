"""Tests for CDDBS platform adapters (production)."""

import pytest
from datetime import datetime

from src.cddbs.adapters import (
    TwitterAdapter,
    TelegramAdapter,
    PlatformAdapter,
    BriefingInput,
    PostData,
    ProfileData,
)


# --- Twitter Adapter Tests ---

class TestTwitterAdapter:
    """Tests for Twitter/X API v2 data normalization."""

    @pytest.fixture
    def adapter(self):
        return TwitterAdapter()

    @pytest.fixture
    def raw_twitter_profile(self):
        return {
            "username": "rt_com",
            "name": "RT",
            "description": "RT is the first Russian 24/7 English-language news channel.",
            "created_at": "2009-03-14T00:00:00Z",
            "verified": False,
            "is_blue_verified": False,
            "lang": "en",
            "public_metrics": {
                "followers_count": 3180000,
                "following_count": 1247,
                "tweet_count": 245000,
                "listed_count": 15000,
            },
        }

    @pytest.fixture
    def raw_twitter_tweet(self):
        return {
            "id": "1234567890",
            "text": "NATO expansion continues to threaten European security...",
            "created_at": "2026-02-10T12:00:00Z",
            "lang": "en",
            "public_metrics": {
                "like_count": 150,
                "retweet_count": 200,
                "reply_count": 45,
                "quote_count": 30,
                "impression_count": 50000,
            },
            "entities": {
                "urls": [{"expanded_url": "https://rt.com/article/123"}],
                "mentions": [{"username": "SputnikInt"}],
            },
            "referenced_tweets": [],
        }

    def test_platform_type(self, adapter):
        assert adapter.platform == "twitter"

    def test_normalize_profile(self, adapter, raw_twitter_profile):
        profile = adapter.normalize_profile(raw_twitter_profile)
        assert isinstance(profile, ProfileData)
        assert profile.handle == "@rt_com"
        assert profile.platform == "twitter"
        assert profile.display_name == "RT"
        assert profile.followers == 3180000
        assert profile.following == 1247
        assert profile.total_posts == 245000
        assert profile.created_at == "2009-03-14"

    def test_normalize_profile_metadata(self, adapter, raw_twitter_profile):
        profile = adapter.normalize_profile(raw_twitter_profile)
        assert "twitter_list_memberships" in profile.platform_metadata
        assert profile.platform_metadata["twitter_list_memberships"] == 15000

    def test_normalize_tweet(self, adapter, raw_twitter_tweet):
        post = adapter.normalize_post(raw_twitter_tweet)
        assert isinstance(post, PostData)
        assert post.post_id == "1234567890"
        assert "NATO" in post.text
        assert post.engagement["likes"] == 150
        assert post.engagement["retweets"] == 200
        assert not post.is_amplification

    def test_normalize_retweet(self, adapter, raw_twitter_tweet):
        raw_twitter_tweet["referenced_tweets"] = [
            {"type": "retweeted", "author_username": "SputnikInt"}
        ]
        post = adapter.normalize_post(raw_twitter_tweet)
        assert post.is_amplification is True
        assert post.amplification_source == "SputnikInt"

    def test_normalize_extracts_urls(self, adapter, raw_twitter_tweet):
        post = adapter.normalize_post(raw_twitter_tweet)
        assert len(post.urls) == 1
        assert "rt.com" in post.urls[0]

    def test_normalize_extracts_mentions(self, adapter, raw_twitter_tweet):
        post = adapter.normalize_post(raw_twitter_tweet)
        assert "@SputnikInt" in post.mentions

    def test_full_normalize(self, adapter, raw_twitter_profile, raw_twitter_tweet):
        raw_data = {
            "profile": raw_twitter_profile,
            "posts": [raw_twitter_tweet],
            "collection_period": {"start": "2026-01-01", "end": "2026-02-10"},
            "data_source": "twitter_api_v2",
        }
        result = adapter.normalize(raw_data)
        assert isinstance(result, BriefingInput)
        assert result.profile.platform == "twitter"
        assert len(result.posts) == 1
        assert result.data_source == "twitter_api_v2"

    def test_empty_profile(self, adapter):
        profile = adapter.normalize_profile({})
        assert profile.handle == "@"
        assert profile.platform == "twitter"
        assert profile.followers == 0


# --- Telegram Adapter Tests ---

class TestTelegramAdapter:
    """Tests for Telegram MTProto/Bot API data normalization."""

    @pytest.fixture
    def adapter(self):
        return TelegramAdapter()

    @pytest.fixture
    def raw_telegram_channel(self):
        return {
            "username": "rt_english",
            "title": "RT English",
            "description": "RT is a global news network.",
            "type": "channel",
            "members_count": 524000,
            "verified": False,
            "date": 1577836800,  # 2020-01-01 UTC
            "lang": "en",
            "linked_chat_username": "rt_english_chat",
            "invite_link": "t.me/rt_english",
            "message_count": 45000,
        }

    @pytest.fixture
    def raw_telegram_message(self):
        return {
            "message_id": 98765,
            "text": "NATO continues military buildup near Russian borders...",
            "date": 1707566400,  # 2024-02-10 12:00:00 UTC
            "views": 85000,
            "forwards": 234,
            "reply_count": 12,
            "entities": [
                {"type": "url", "offset": 0, "length": 0},
                {"type": "mention", "offset": 50, "length": 10},
            ],
        }

    @pytest.fixture
    def raw_telegram_forward(self):
        return {
            "message_id": 98766,
            "text": "Content originally from RT Russian channel",
            "date": 1707566500,
            "views": 45000,
            "forwards": 100,
            "forward_from_chat": {
                "username": "rt_russian",
                "title": "RT na russkom",
            },
            "forward_date": 1707566400,
        }

    def test_platform_type(self, adapter):
        assert adapter.platform == "telegram"

    def test_normalize_channel_profile(self, adapter, raw_telegram_channel):
        profile = adapter.normalize_profile(raw_telegram_channel)
        assert isinstance(profile, ProfileData)
        assert profile.handle == "@rt_english"
        assert profile.platform == "telegram"
        assert profile.display_name == "RT English"
        assert profile.followers == 524000
        assert profile.following == 0  # Channels don't follow
        assert profile.created_at == "2020-01-01"

    def test_normalize_channel_metadata(self, adapter, raw_telegram_channel):
        profile = adapter.normalize_profile(raw_telegram_channel)
        meta = profile.platform_metadata
        assert meta["telegram_channel_type"] == "channel"
        assert meta["telegram_subscriber_count"] == 524000
        assert meta["telegram_linked_chat"] == "rt_english_chat"

    def test_normalize_message(self, adapter, raw_telegram_message):
        post = adapter.normalize_post(raw_telegram_message)
        assert isinstance(post, PostData)
        assert post.post_id == "98765"
        assert "NATO" in post.text
        assert post.engagement["views"] == 85000
        assert not post.is_amplification

    def test_normalize_forwarded_message(self, adapter, raw_telegram_forward):
        post = adapter.normalize_post(raw_telegram_forward)
        assert post.is_amplification is True
        assert post.amplification_source == "rt_russian"

    def test_normalize_message_with_media(self, adapter, raw_telegram_message):
        raw_telegram_message["photo"] = [{"file_id": "abc123"}]
        post = adapter.normalize_post(raw_telegram_message)
        assert post.media_type == "image"

    def test_normalize_message_with_video(self, adapter, raw_telegram_message):
        raw_telegram_message["video"] = {"file_id": "vid123"}
        post = adapter.normalize_post(raw_telegram_message)
        assert post.media_type == "video"

    def test_full_normalize(self, adapter, raw_telegram_channel, raw_telegram_message, raw_telegram_forward):
        raw_data = {
            "profile": raw_telegram_channel,
            "posts": [raw_telegram_message, raw_telegram_forward],
            "collection_period": {"start": "2026-01-15", "end": "2026-03-07"},
            "data_source": "telegram_mtproto",
        }
        result = adapter.normalize(raw_data)
        assert isinstance(result, BriefingInput)
        assert result.profile.platform == "telegram"
        assert len(result.posts) == 2
        assert result.data_source == "telegram_mtproto"

    def test_empty_channel(self, adapter):
        profile = adapter.normalize_profile({})
        assert profile.handle == "@"
        assert profile.platform == "telegram"
        assert profile.followers == 0

    def test_telegram_unix_timestamp_parsing(self, adapter, raw_telegram_channel):
        profile = adapter.normalize_profile(raw_telegram_channel)
        assert profile.created_at == "2020-01-01"


# --- Cross-Platform Tests ---

class TestCrossPlatformNormalization:
    """Test that data from different platforms normalizes to a comparable format."""

    def test_both_adapters_produce_briefing_input(self):
        twitter = TwitterAdapter().normalize({"profile": {"username": "test"}, "posts": []})
        telegram = TelegramAdapter().normalize({"profile": {"username": "test"}, "posts": []})
        assert isinstance(twitter, BriefingInput)
        assert isinstance(telegram, BriefingInput)

    def test_profile_fields_consistent(self):
        tw_profile = TwitterAdapter().normalize_profile({"username": "test", "public_metrics": {"followers_count": 100}})
        tg_profile = TelegramAdapter().normalize_profile({"username": "test", "members_count": 100})
        # Both should have the same core fields populated
        assert tw_profile.followers == 100
        assert tg_profile.followers == 100

    def test_amplification_detection_cross_platform(self):
        tw_post = TwitterAdapter().normalize_post({
            "id": "1", "text": "test", "created_at": "2026-01-01T00:00:00Z",
            "referenced_tweets": [{"type": "retweeted", "author_username": "source"}],
            "public_metrics": {},
        })
        tg_post = TelegramAdapter().normalize_post({
            "message_id": 1, "text": "test", "date": 1704067200,
            "forward_from_chat": {"username": "source", "title": "Source"},
        })
        assert tw_post.is_amplification is True
        assert tg_post.is_amplification is True
