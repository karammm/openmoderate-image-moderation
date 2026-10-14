# Security policy

## Supported versions

Security fixes are released for the latest minor version of openmoderate (currently 1.0.x).

## Reporting a vulnerability

**Please do not open a public issue for security problems.** Report them privately through
[GitHub security advisories](https://github.com/karammm/openmoderate-image-moderation/security/advisories/new).
We aim to acknowledge reports within 3 working days and to publish a fix or mitigation
within 30 days.

Useful things to include: the affected version, a description of the impact, and the
smallest reproduction you can share.

## Scope

In scope:

- The REST server: authentication bypass, SSRF through URL fetching, denial of service
  through crafted uploads that bypass the size, duration or frame limits.
- Loading files: code execution or crashes from crafted images, videos or `.omh` head files.
- The framework integrations: uploads that skip moderation.

**Model evasion** (an image crafted to get a low score) is a known limitation of every
machine-learning moderator rather than a vulnerability. Please report systematic misses
as a regular issue using the *Misclassification* template — and never attach the
harmful image itself.

## Hardening advice for operators

- Always set `OPENMODERATE_API_KEY` when the server is reachable by anyone else.
- Leave URL fetching off (`OPENMODERATE_ALLOW_URLS`) unless you need it; if you enable
  it for untrusted callers, route outbound traffic through an egress proxy.
- Video decoding runs FFmpeg on untrusted input: run the server in a container with
  limited memory and no access to internal networks.
- Only load `.omh` heads and policy files from sources you trust. `.omh` files contain
  no executable code, but a malicious head can still make the moderator approve content.
