"""LinkedIn posting tool for JARVIS.

Publishes text posts — and text posts with an image — to the user's
LinkedIn profile via the current Posts API (POST /rest/posts). The old
/v2/ugcPosts endpoint is retired. Can also delete a post.

Needs LINKEDIN_ACCESS_TOKEN (OAuth token with the w_member_social scope,
from the "Share on LinkedIn" product) in env vars. The author URN is
fetched automatically from the OpenID userinfo endpoint, so
LINKEDIN_PERSON_URN is optional — set it only to skip that lookup.

Image posts: the image is given as a public URL, downloaded server-side,
uploaded to LinkedIn's media service (registerUpload → PUT bytes), then
attached to the post as a media asset.
"""
import json
import os
import urllib.parse
import urllib.request
import urllib.error

import requests

LINKEDIN_VERSION = "202601"  # YYYYMM — pin a recent version; old ones sunset
_MAX_IMAGE_BYTES = 8 * 1024 * 1024  # LinkedIn image posts cap well above this


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


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _post_payload(author_urn: str, text: str, media: list | None = None) -> dict:
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
    if media:
        payload["media"] = media
    return payload


def _submit_post(token: str, payload: dict) -> str:
    """POST /rest/posts; returns the same style message as before."""
    try:
        req = urllib.request.Request(
            "https://api.linkedin.com/rest/posts",
            data=json.dumps(payload).encode("utf-8"),
            headers=_headers(token),
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
        msg = "Posted to LinkedIn, Sir (status 201)."
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

    return _submit_post(token, _post_payload(author_urn, text))


def _download_image(image_url: str) -> tuple[bytes | None, str, str]:
    """Fetch an image from a public URL. Returns (bytes, content-type, error)."""
    parsed = urllib.parse.urlparse(image_url or "")
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None, "", "That image URL does not look valid, Sir."
    try:
        res = requests.get(
            image_url,
            timeout=15,
            stream=True,
            headers={"User-Agent": "JARVIS/1.0"},
        )
        res.raise_for_status()
        content_type = (res.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type and not content_type.startswith("image/"):
            return None, "", "That URL is not an image, Sir."
        data = b""
        for chunk in res.iter_content(chunk_size=65536):
            data += chunk
            if len(data) > _MAX_IMAGE_BYTES:
                return None, "", "That image is too big for LinkedIn, Sir (over 8 MB)."
        if not data:
            return None, "", "I could not download that image, Sir — it came back empty."
        if not content_type:
            content_type = "image/jpeg"
        return data, content_type, ""
    except requests.RequestException as e:
        return None, "", f"I could not download that image, Sir: {e}"


def _register_image_upload(token: str, author_urn: str) -> tuple[str, str, str]:
    """Register an image upload. Returns (upload_url, asset_urn, error)."""
    body = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": author_urn,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }
            ],
        }
    }
    try:
        req = urllib.request.Request(
            "https://api.linkedin.com/v2/assets?action=registerUpload",
            data=json.dumps(body).encode("utf-8"),
            headers=_headers(token),
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            result = json.loads(res.read().decode("utf-8"))
        value = result.get("value", {})
        upload_url = value.get("uploadMechanism", {}).get(
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {}
        ).get("uploadUrl", "")
        asset = value.get("asset", "")
        if not upload_url or not asset:
            return "", "", "LinkedIn did not give me an upload slot for the image, Sir."
        return upload_url, asset, ""
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8")[:300]
        except Exception:
            detail = ""
        return "", "", f"LinkedIn image upload failed (HTTP {e.code}). {detail}"
    except Exception as e:
        return "", "", f"LinkedIn image upload failed: {e}"


def _upload_image_bytes(upload_url: str, data: bytes, content_type: str) -> str:
    """PUT the image bytes to LinkedIn's signed upload URL. Returns error or ''."""
    try:
        req = urllib.request.Request(
            upload_url,
            data=data,
            method="PUT",
            headers={"Content-Type": content_type},
        )
        with urllib.request.urlopen(req, timeout=30):
            pass
        return ""
    except urllib.error.HTTPError as e:
        return f"LinkedIn image upload failed (HTTP {e.code})."
    except Exception as e:
        return f"LinkedIn image upload failed: {e}"


def post_to_linkedin_with_image(text: str, image_url: str, alt_text: str = "") -> str:
    """Publishes a post with an image to the user's LinkedIn profile.

    image_url must be a public image URL (downloaded server-side, max 8 MB).
    alt_text is a short description of the image for accessibility.
    """
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        return ("LinkedIn is not set up, Sir — add LINKEDIN_ACCESS_TOKEN "
                "in Render environment variables first.")
    if not (text or "").strip():
        return "What should I post to LinkedIn, Sir?"
    if not (image_url or "").strip():
        return "Which image should I attach to the LinkedIn post, Sir?"

    data, content_type, err = _download_image(image_url.strip())
    if err:
        return err

    author_urn = os.environ.get("LINKEDIN_PERSON_URN") or _get_person_urn(token)
    if not author_urn:
        return ("LinkedIn post failed, Sir — I could not work out your "
                "profile ID. Check the access token and try again.")

    upload_url, asset, err = _register_image_upload(token, author_urn)
    if err:
        return err
    err = _upload_image_bytes(upload_url, data, content_type)
    if err:
        return err

    media = [{"id": asset, "altText": (alt_text or "").strip()}]
    return _submit_post(token, _post_payload(author_urn, text, media=media))


def delete_linkedin_post(post: str) -> str:
    """Deletes a LinkedIn post by its URN (urn:li:share:... / urn:li:ugcPost:...)
    or a bare post id. Falls back to the legacy /v2/ugcPosts endpoint if the
    current Posts API rejects the delete."""
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        return ("LinkedIn is not set up, Sir — add LINKEDIN_ACCESS_TOKEN "
                "in Render environment variables first.")
    post = (post or "").strip()
    if not post:
        return "Which LinkedIn post should I delete, Sir?"

    if post.startswith("urn:li:"):
        urn = post
    else:
        # A bare id — assume a share id; the ugcPost fallback covers the rest.
        urn = f"urn:li:share:{post}"
    post_id = urn.rsplit(":", 1)[-1]

    def _try_delete(url: str) -> tuple[bool, str]:
        try:
            req = urllib.request.Request(
                url,
                method="DELETE",
                headers={
                    "Authorization": f"Bearer {token}",
                    "LinkedIn-Version": LINKEDIN_VERSION,
                    "X-Restli-Protocol-Version": "2.0.0",
                },
            )
            with urllib.request.urlopen(req, timeout=10):
                pass
            return True, ""
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8")[:300]
            except Exception:
                detail = ""
            return False, f"HTTP {e.code}. {detail}"
        except Exception as e:
            return False, str(e)

    ok, err = _try_delete(
        "https://api.linkedin.com/rest/posts/" + urllib.parse.quote(urn, safe="")
    )
    if ok:
        return "Deleted that LinkedIn post, Sir."
    # Fall back to the legacy endpoint with the bare id.
    ok, err2 = _try_delete(f"https://api.linkedin.com/v2/ugcPosts/{post_id}")
    if ok:
        return "Deleted that LinkedIn post, Sir."
    return f"LinkedIn delete failed, Sir — {err or err2}"
