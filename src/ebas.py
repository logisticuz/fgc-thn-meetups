"""
eBas/Sverok membership registration via n8n webhook.

Calls the shared n8n workflow (webhook/ebas/register-v2) which handles:
- Personnummer normalization (10→12 digits)
- Setting renewal date to today
- Calling Sverok eBas API (submit_member_with_lookup)
- SPAR lookup for name (we don't need to send first/last name)

The response comes synchronously (responseMode: lastNode).
The n8n callback to /api/checkin/{id}/member-status fails silently
since we send checkin_id="" — this is by design.
"""

import logging
import httpx
from src.config import settings

logger = logging.getLogger(__name__)


async def register_member(
    personnummer: str,
    tag: str,
    email: str = "",
    telephone: str = "",
) -> dict:
    """
    Register a Sverok member via n8n → eBas.

    Returns the n8n response dict, e.g.:
        {"success": True, "registered": True, "message": "Medlem registrerad i Sverok"}
    or on error:
        {"success": False, "error": True, "message": "..."}
    """
    payload = {
        "personnummer": personnummer,
        "email": email,
        "telephone": telephone,
        "tag": tag,
        "slug": "meetup",
        "checkin_id": "",
    }

    url = f"{settings.n8n_url}/webhook/ebas/register-v2"
    logger.info(f"eBas register: tag={tag}, url={url}")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"eBas result: {result.get('message', 'no message')}")
            return result
    except httpx.TimeoutException:
        logger.error("eBas register timeout")
        return {"success": False, "error": True, "message": "Timeout vid kontakt med Sverok"}
    except httpx.HTTPStatusError as e:
        logger.error(f"eBas register HTTP error: {e.response.status_code}")
        return {"success": False, "error": True, "message": f"HTTP-fel: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"eBas register error: {e}")
        return {"success": False, "error": True, "message": "Kunde inte kontakta Sverok"}
