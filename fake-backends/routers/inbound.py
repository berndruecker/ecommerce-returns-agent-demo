import json
import logging
from typing import Dict, List
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import Response
import httpx

try:
    import xmltodict  # type: ignore
except Exception:
    xmltodict = None  # Fallback if not installed; will handle at runtime


router = APIRouter()
logger = logging.getLogger("fake-services.inbound-proxy")

TARGET_BASE = "http://localhost:8086"


def _is_xml_content(content_type: str | None) -> bool:
    if not content_type:
        return False
    ct = content_type.lower()
    return "xml" in ct


def _xml_to_json_bytes(xml_body: bytes) -> bytes:
    if xmltodict is None:
        # If xmltodict is not installed, pass original body through to avoid failure
        logger.warning("xmltodict not available; passing XML through unchanged")
        return xml_body
    try:
        obj = xmltodict.parse(xml_body)
        return json.dumps(obj).encode("utf-8")
    except Exception as exc:
        logger.error(
            "XML→JSON conversion failed: error=%s body_preview=%s",
            str(exc),
            xml_body[:512].decode("utf-8", errors="replace"),
        )
        # If conversion fails, return the original body to avoid dropping data
        return xml_body


def _json_to_xml_bytes(json_body: bytes) -> bytes:
    if xmltodict is None:
        logger.warning("xmltodict not available; passing JSON through unchanged")
        return json_body
    try:
        obj = json.loads(json_body)
        xml_str = xmltodict.unparse(obj, pretty=True)
        return xml_str.encode("utf-8")
    except Exception as exc:
        logger.error(
            "JSON→XML conversion failed: error=%s body_preview=%s",
            str(exc),
            json_body[:512].decode("utf-8", errors="replace"),
        )
        # If conversion fails, return the original body
        return json_body


async def _forward(request: Request, target_path: str, convert_xml: bool, convert_response: bool = False) -> Response:
    # Build target URL with original query string
    target_url = f"{TARGET_BASE}{target_path}"

    # Read incoming request data
    method = request.method
    query = request.url.query
    body = await request.body()
    orig_content_type = request.headers.get("content-type")

    # Prepare headers, excluding hop-by-hop and overriding Host
    headers: Dict[str, str] = {}
    for k, v in request.headers.items():
        lk = k.lower()
        if lk in {"host", "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"}:
            continue
        headers[k] = v

    # XML → JSON conversion when requested, or form→JSON (Twilio style)
    did_convert = False
    if convert_xml and body:
        if _is_xml_content(orig_content_type):
            body = _xml_to_json_bytes(body)
            did_convert = True
        elif orig_content_type and "application/x-www-form-urlencoded" in orig_content_type.lower():
            form_text = body.decode("utf-8", errors="replace")
            form_dict = parse_qs(form_text, keep_blank_values=True)
            normalized: Dict[str, List[str] | str] = {}
            for k, v in form_dict.items():
                normalized[k] = v[0] if len(v) == 1 else v
            body = json.dumps(normalized).encode("utf-8")
            did_convert = True

    # If we converted the body, ensure headers reflect JSON and let httpx recalc length
    if did_convert:
        # Remove any pre-existing content-type and content-length (case-insensitive)
        for hk in list(headers.keys()):
            if hk.lower() in {"content-type", "content-length"}:
                headers.pop(hk, None)
        headers["Content-Type"] = "application/json"

    def _sanitize_headers(h: Dict[str, str]) -> Dict[str, str]:
        redacted = {}
        for hk, hv in h.items():
            if hk.lower() in {"authorization", "cookie", "set-cookie"}:
                redacted[hk] = "<redacted>"
            else:
                redacted[hk] = hv
        return redacted

    def _preview_bytes(b: bytes, limit: int = 1024) -> str:
        if not b:
            return ""
        return b[:limit].decode("utf-8", errors="replace")

    full_url = target_url if not query else f"{target_url}?{query}"

    # Log original and final forwarded request details
    logger.info(
        (
            "Preparing upstream request: method=%s url=%s convert_xml=%s did_convert=%s original_content_type=%s"
        ),
        method,
        full_url,
        str(convert_xml),
        str(did_convert),
        str(orig_content_type),
    )
    logger.info(
        (
            "Forwarding upstream request (final): method=%s url=%s forward_content_type=%s headers=%s body_preview=%s"
        ),
        method,
        full_url,
        str(headers.get("Content-Type")),
        str(_sanitize_headers(headers)),
        _preview_bytes(body),
    )

    # Execute forward request
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method=method,
                url=full_url,
                content=body,
                headers=headers,
            )
    except httpx.RequestError as exc:
        logger.error(
            (
                "Upstream request failed: method=%s url=%s headers=%s body_preview=%s error=%s"
            ),
            method,
            full_url,
            str(_sanitize_headers(headers)),
            _preview_bytes(body),
            str(exc),
        )
        return Response(
            content=json.dumps({"error": "Upstream request failed", "detail": str(exc)}),
            status_code=502,
            media_type="application/json",
        )
    except Exception as exc:
        logger.exception(
            (
                "Unexpected error forwarding request: method=%s url=%s headers=%s body_preview=%s error=%s"
            ),
            method,
            full_url,
            str(_sanitize_headers(headers)),
            _preview_bytes(body),
            str(exc),
        )
        return Response(
            content=json.dumps({"error": "Unexpected error", "detail": str(exc)}),
            status_code=500,
            media_type="application/json",
        )

    # Prepare response back to caller
    # Filter out hop-by-hop headers
    resp_headers: List[tuple[str, str]] = [
        (k, v)
        for k, v in resp.headers.items()
        if k.lower()
        not in {
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade",
            "content-type",  # Remove original content-type, we'll set it explicitly
        }
    ]

    # Log upstream response (always)
    logger.info(
        (
            "Upstream responded: method=%s url=%s status_code=%s response_headers=%s response_body_preview=%s"
        ),
        method,
        full_url,
        str(resp.status_code),
        str(_sanitize_headers(dict(resp.headers))),
        _preview_bytes(resp.content),
    )

    # JSON → XML conversion for response (if enabled and response is JSON)
    resp_body = resp.content
    resp_content_type = resp.headers.get("content-type", "")
    did_convert_response = False
    if convert_response and "application/json" in resp_content_type.lower() and resp_body:
        resp_body = _json_to_xml_bytes(resp_body)
        did_convert_response = True
        resp_content_type = "application/xml"
        logger.info(
            "Converted response JSON→XML: original_content_type=%s final_content_type=%s body_preview=%s",
            str(resp.headers.get("content-type")),
            "application/xml",
            _preview_bytes(resp_body),
        )

    # Log non-success statuses with context
    if resp.status_code >= 400:
        logger.error(
            (
                "Upstream responded with error: method=%s url=%s status_code=%s "
                "request_headers=%s request_body_preview=%s response_headers=%s response_body_preview=%s"
            ),
            method,
            full_url,
            str(resp.status_code),
            str(_sanitize_headers(headers)),
            _preview_bytes(body),
            str(_sanitize_headers(dict(resp.headers))),
            _preview_bytes(resp.content),
        )

    return Response(content=resp_body, status_code=resp.status_code, headers=dict(resp_headers), media_type=resp_content_type)


# Twilio webhook passthrough
@router.api_route("/twilio", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]) 
async def proxy_twilio(request: Request):
    """Forward any request on /inbound/twilio to Camunda unchanged."""
    logger.info("Proxy /inbound/twilio -> %s", f"{TARGET_BASE}/inbound/twilio")
    return await _forward(request, "/inbound/twilio", convert_xml=False)


HOLD_LOOP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Danielle-Neural">One moment.</Say>
    <Pause length="5"/>
    <Pause length="5"/>
    <Pause length="5"/>
    <Pause length="5"/>
    <Redirect method="POST">https://catarina-unnicked-famishedly.ngrok-free.dev/inbound/twilio/hold-loop</Redirect>
</Response>
"""


# Voice endpoints: convert form/XML payloads to JSON on the fly, and convert JSON responses back to XML
@router.api_route("/voice", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]) 
async def proxy_voice(request: Request):
    logger.info("Proxy /inbound/voice (form/XML→JSON, JSON→XML) -> %s", f"{TARGET_BASE}/inbound/voice")
    return await _forward(request, "/inbound/voice", convert_xml=True, convert_response=True)


@router.api_route("/voice-answer", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]) 
async def proxy_voice_answer(request: Request):
    logger.info("Proxy /inbound/voice-answer (form/XML→JSON, JSON→XML) -> %s", f"{TARGET_BASE}/inbound/voice-answer")
    return await _forward(request, "/inbound/voice-answer", convert_xml=True, convert_response=True)


@router.api_route("/voice-ask", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]) 
async def proxy_voice_ask(request: Request):
    logger.info("Proxy /inbound/voice-ask (form/XML→JSON, JSON→XML) -> %s", f"{TARGET_BASE}/inbound/voice-ask")
    return await _forward(request, "/inbound/voice-ask", convert_xml=True, convert_response=True)


@router.api_route("/voice-ended", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]) 
async def proxy_voice_ended(request: Request):
    logger.info("Proxy /inbound/voice-ended (form/XML→JSON, JSON→XML) -> %s", f"{TARGET_BASE}/inbound/voice-ended")
    return await _forward(request, "/inbound/voice-ended", convert_xml=True, convert_response=True)


@router.api_route("/twilio/hold-loop", methods=["GET", "POST"]) 
async def twilio_hold_loop():
    """Serve a static Twilio hold-loop TwiML."""
    return Response(content=HOLD_LOOP_XML.strip(), media_type="application/xml")
