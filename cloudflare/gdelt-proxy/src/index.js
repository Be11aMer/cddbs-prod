/**
 * GDELT Doc API v2 proxy
 *
 * Forwards requests to api.gdeltproject.org, bypassing IP-based rate limits
 * that GDELT applies to datacenter IP ranges (Render, Fly, etc.).
 * Cloudflare edge IPs are not flagged as datacenter scraper traffic.
 *
 * The backend calls this Worker instead of hitting GDELT directly.
 * Set GDELT_PROXY_URL=https://gdelt-proxy.<account>.workers.dev in Fly.io secrets.
 */

const GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc";

export default {
  async fetch(request, env) {
    // Only allow GET
    if (request.method !== "GET") {
      return new Response("Method not allowed", { status: 405 });
    }

    // Forward all query params (query, mode, maxrecords, format, timespan, sort)
    const incoming = new URL(request.url);
    const target = new URL(GDELT_URL);
    target.search = incoming.search;

    let response;
    try {
      response = await fetch(target.toString(), {
        headers: {
          // Identify as a legitimate research tool
          "User-Agent": "CDDBS-Research/1.0 (Disinformation Detection; academic use)",
          "Accept": "application/json, */*",
        },
        cf: {
          // Don't cache on Cloudflare's side — GDELT is real-time
          cacheEverything: false,
        },
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: "GDELT upstream unreachable", detail: String(err) }), {
        status: 502,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Pass content-type through; strip headers that would confuse the Python client
    const headers = new Headers();
    const ct = response.headers.get("content-type");
    if (ct) headers.set("Content-Type", ct);

    return new Response(response.body, {
      status: response.status,
      headers,
    });
  },
};
