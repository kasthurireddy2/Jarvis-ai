"""LinkedIn posting tool for JARVIS.

Publishes a text post to the user's LinkedIn profile via the UGC API.
Needs LINKEDIN_ACCESS_TOKEN (OAuth token with the w_member_social scope)
and LINKEDIN_PERSON_URN (e.g. "urn:li:person:xxxxxx") in env vars.
"""
import json
import os
import urllib.request
import urllib.error


def post_to_linkedin(text: str) -> str:
    """Publishes a text post to the user's LinkedIn profile."""
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    author_urn = os.environ.get("LINKEDIN_PERSON_URN")  # e.g. "urn:li:person:xxxxxx"
    if not token or not author_urn:
        return ("LinkedIn is not set up, Sir — add LINKEDIN_ACCESS_TOKEN and "
                "LINKEDIN_PERSON_URN in Render environment variables first.")
    if not (text or "").strip():
        return "What should I post to LinkedIn, Sir?"

    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text.strip()},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    try:
        req = urllib.request.Request(
            "https://api.linkedin.com/v2/ugcPosts",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            return f"Posted to LinkedIn, Sir (status {res.status})."
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8")[:300]
        except Exception:
            detail = ""
        return f"LinkedIn post failed (HTTP {e.code}). {detail}"
    except Exception as e:
        return f"LinkedIn post failed: {e}"
