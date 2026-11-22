"""LinkedIn posting tool for JARVIS.

Publishes a text post to the user's LinkedIn profile via the current
Posts API (POST /rest/posts). The old /v2/ugcPosts endpoint is retired.

Needs LINKEDIN_ACCESS_TOKEN (OAuth token with the w_member_social scope,
from the "Share on LinkedIn" product) in env vars. The author URN is
fetched automatically from the OpenID userinfo endpoint, so
LINKEDIN_PERSON_URN is optional — set it only to skip that lookup.
"""
import json
import os
import urllib.request
import urllib.error

LINKEDIN_VERSION = "202601"  # YYYYMM — pin a recent version; old ones sunset


def _get_person_urn(token: str) -> str | None:
    """Fetch the member's person URN via the OpenID userinfo endpoint."""
    try:
        req = urllib.request.Request(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            sub = json.loads(res.read().decode("utf-8")).get("sub")
        return f"urn:li:person:{sub}" if sub else None
    except Exception:
        return None


def post_to_linkedin(text: str) -> str:
    """Publishes a text post to the user's LinkedIn profile."""
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        return ("LinkedIn is not set up, Sir — add LINKEDIN_ACCESS_TOKEN "
                "in Render environment variables first.")
    if not (text or "").strip():
        return "What should I post to LinkedIn, Sir?"

    author_urn = os.environ.get("LINKEDIN_PERSON_URN") or _get_person_urn(token)
    if not author_urn:
        return ("LinkedIn post failed, Sir — I could not work out your "
                "profile ID. Check the access token and try again.")

    payload = {
        "author": author_urn,
        "commentary": text.strip(),
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    try:
        req = urllib.request.Request(
            "https://api.linkedin.com/rest/posts",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "LinkedIn-Version": LINKEDIN_VERSION,
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            body = res.read().decode("utf-8")
        # The 201 body carries the new post's id, e.g. {"id": "urn:li:share:..."}.
        post_id = ""
        try:
            post_id = json.loads(body).get("id", "") or ""
        except Exception:
            post_id = ""
        link = f"https://www.linkedin.com/feed/update/{post_id}" if post_id else ""
        msg = f"Posted to LinkedIn, Sir (status 201)."
        if link:
            msg += f" Link: {link}"
        return msg
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8")[:300]
        except Exception:
            detail = ""
        return f"LinkedIn post failed (HTTP {e.code}). {detail}"
    except Exception as e:
        return f"LinkedIn post failed: {e}"
