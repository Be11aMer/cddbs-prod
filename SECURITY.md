# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| Latest `main` branch | Yes |
| Older commits | No |

## Reporting a Vulnerability

If you discover a security vulnerability in CDDBS, **please do not open a public issue.**

Instead, report it privately:

1. Go to the [Security Advisories](https://github.com/Be11aMer/cddbs-prod/security/advisories) page
2. Click **"Report a vulnerability"**
3. Provide a detailed description of the issue, steps to reproduce, and potential impact

You can expect:
- **Acknowledgement** within 48 hours
- **Status update** within 7 days
- **Fix or mitigation** as soon as practically possible

## Scope

The following are in scope for security reports:
- Authentication or authorization bypasses
- SQL injection, XSS, or other injection attacks
- Exposure of API keys, tokens, or credentials
- Server-side request forgery (SSRF)
- Vulnerabilities in dependencies

## Out of Scope

- Denial of service (DoS) attacks
- Social engineering
- Issues in third-party services (SerpAPI, Google AI, Twitter, Telegram)
- Issues requiring physical access

## Security Best Practices for Contributors

- Never commit API keys, tokens, or credentials — use environment variables
- Keep dependencies up to date
- Follow the principle of least privilege in code
- All secrets must go through environment variables defined in `config.py`
