"""SSRF guard tests for webhook URLs (finding N-2).

validate_webhook_url must reject URLs that could drive server-side request
forgery (private/loopback/link-local/metadata/reserved hosts, and non-http
schemes) while allowing publicly-routable http/https targets. All cases use
IP literals so no DNS lookup (and no network) is required.
"""
import pytest

from src.cddbs.webhooks import validate_webhook_url, WebhookURLError


class TestWebhookSSRFGuard:
    @pytest.mark.parametrize("url", [
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata (link-local)
        "http://127.0.0.1:8000/hook",                 # loopback
        "http://10.0.0.5/hook",                        # private (RFC1918)
        "http://192.168.1.10/hook",                    # private (RFC1918)
        "http://172.16.0.1/hook",                      # private (RFC1918)
        "http://[::1]/hook",                           # loopback (IPv6)
        "http://0.0.0.0/hook",                         # unspecified
    ])
    def test_rejects_internal_targets(self, url):
        with pytest.raises(WebhookURLError):
            validate_webhook_url(url)

    @pytest.mark.parametrize("url", [
        "file:///etc/passwd",
        "ftp://198.51.100.1/x",
        "gopher://198.51.100.1/x",
    ])
    def test_rejects_non_http_schemes(self, url):
        with pytest.raises(WebhookURLError):
            validate_webhook_url(url)

    @pytest.mark.parametrize("url", ["", None, "https://", "not-a-url"])
    def test_rejects_malformed(self, url):
        with pytest.raises(WebhookURLError):
            validate_webhook_url(url)

    @pytest.mark.parametrize("url", [
        "https://8.8.8.8/hook",         # public IPv4 literal
        "http://1.1.1.1:9000/hook",     # public IPv4 literal, non-default port
    ])
    def test_allows_public_targets(self, url):
        # Should not raise for publicly-routable hosts.
        validate_webhook_url(url)
