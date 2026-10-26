"""Authenticated local MCP endpoint. This release exposes no Home Assistant write tools."""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

import yaml
import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from mcp.server.fastmcp import FastMCP

from .safety import ProposalStore

OPTIONS_PATH = Path(os.environ.get("HA_MCP_OPTIONS_PATH", "/data/options.json"))


def load_options(path: Path = OPTIONS_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Could not read add-on options; configure them in the Home Assistant UI") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Invalid add-on options")
    return value


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str, allowed_hosts: set[str]):
        super().__init__(app)
        self.token = token
        self.allowed_hosts = allowed_hosts

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return JSONResponse({"status": "ok", "mode": "read-only", "writes_enabled": False})
        host = request.headers.get("host", "").lower()
        if host not in self.allowed_hosts:
            return JSONResponse({"error": "host_not_allowed"}, status_code=421)
        # Browser-origin requests are denied; use a local MCP client without an Origin header.
        if request.headers.get("origin"):
            return JSONResponse({"error": "browser_origin_not_allowed"}, status_code=403)
        auth = request.headers.get("authorization", "")
        scheme, _, supplied = auth.partition(" ")
        if scheme.lower() != "bearer" or not supplied or not secrets.compare_digest(supplied, self.token):
            return JSONResponse({"error": "unauthorized"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
        return await call_next(request)


mcp = FastMCP(
    "Home Assistant Dashboard Copilot Local Connector",
    instructions=(
        "Local MVP. Read-only by design. Do not claim to inspect live Home Assistant data. "
        "No dashboard write tool is exposed in this version."
    ),
)
proposals = ProposalStore(ttl_seconds=300)
HA_BASE_URL = "http://homeassistant:8123"
HA_TOKEN = ""


async def _ha_get(path: str) -> Any:
    """GET-only Home Assistant API helper. No write methods exist in this module."""
    if not HA_TOKEN:
        raise RuntimeError("Home Assistant token is not configured in the local add-on options")
    async with httpx.AsyncClient(base_url=HA_BASE_URL, timeout=httpx.Timeout(8.0, connect=3.0), follow_redirects=False) as client:
        response = await client.get(path, headers={"Authorization": f"Bearer {HA_TOKEN}", "Accept": "application/json"})
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def connector_status() -> dict[str, Any]:
    """Check connector capabilities and Home Assistant API reachability without changing state."""
    try:
        await _ha_get("/api/")
        connected = True
    except Exception:
        connected = False
    return {
        "status": "ok",
        "mode": "read-only",
        "home_assistant_api_connected": connected,
        "dashboard_write_tools_available": False,
        "write_confirmation_prototype": True,
    }


@mcp.tool()
async def list_entities(domain: str = "", search: str = "", limit: int = 100) -> dict[str, Any]:
    """List a limited, redacted set of entity states; optional domain and entity/name substring filters."""
    if limit < 1 or limit > 250:
        return {"error": "limit must be between 1 and 250", "entities": []}
    if domain and (not domain.replace("_", "").isalnum() or domain.lower() != domain):
        return {"error": "invalid domain filter", "entities": []}
    states = await _ha_get("/api/states")
    if not isinstance(states, list):
        return {"error": "unexpected Home Assistant response", "entities": []}
    needle = search.casefold().strip()
    output = []
    for item in states:
        if not isinstance(item, dict):
            continue
        entity_id = item.get("entity_id", "")
        if not isinstance(entity_id, str) or "." not in entity_id:
            continue
        item_domain = entity_id.split(".", 1)[0]
        attrs = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
        name = attrs.get("friendly_name", "")
        if domain and item_domain != domain:
            continue
        if needle and needle not in entity_id.casefold() and needle not in str(name).casefold():
            continue
        # Deliberately omit full attributes, context, and timestamps to reduce data exposure.
        output.append({"entity_id": entity_id, "state": str(item.get("state", "")), "friendly_name": str(name)})
        if len(output) >= limit:
            break
    return {"count": len(output), "entities": output, "truncated_or_limited": len(output) >= limit}


@mcp.tool()
def validate_dashboard_yaml(dashboard_yaml: str) -> dict[str, Any]:
    """Parse and statically check Lovelace YAML without applying it."""
    if len(dashboard_yaml) > 250_000:
        return {"valid": False, "errors": ["YAML exceeds 250 KB limit"]}
    try:
        parsed = yaml.safe_load(dashboard_yaml)
    except yaml.YAMLError as exc:
        return {"valid": False, "errors": [f"YAML parse error: {type(exc).__name__}"]}
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(parsed, dict):
        errors.append("Top-level YAML value must be a mapping")
    elif not isinstance(parsed.get("views"), list):
        errors.append("Expected a top-level 'views' list")
    else:
        paths: set[str] = set()
        for index, view in enumerate(parsed["views"]):
            if not isinstance(view, dict):
                errors.append(f"views[{index}] must be a mapping")
                continue
            path = view.get("path")
            if path is not None:
                if not isinstance(path, str) or not path.strip():
                    errors.append(f"views[{index}].path must be a non-empty string")
                elif path in paths:
                    errors.append(f"Duplicate view path: {path}")
                else:
                    paths.add(path)
            if "cards" not in view and "sections" not in view:
                warnings.append(f"views[{index}] has neither 'cards' nor 'sections'")
    return {"valid": not errors, "errors": errors, "warnings": warnings,
            "note": "Static validation only; entity IDs and HA-version compatibility are not checked."}


@mcp.tool()
def create_write_proposal(target: str, exact_diff: str) -> dict[str, Any]:
    """Create a proposal only; it does not write to Home Assistant."""
    proposal = proposals.create(target, exact_diff)
    return {
        "proposal_id": proposal.proposal_id,
        "target": proposal.target,
        "exact_diff": proposal.diff,
        "expires_in_seconds": proposals.ttl_seconds,
        "digest": proposal.digest,
        "applied": False,
        "warning": "Proposal only. This release has no write operation and cannot apply changes.",
    }


@mcp.tool()
def confirm_write_proposal(proposal_id: str, target: str, exact_diff: str) -> dict[str, Any]:
    """Record explicit confirmation for the exact proposal, valid once for five minutes."""
    confirmed = proposals.confirm(proposal_id, target, exact_diff)
    return {
        "confirmed": confirmed,
        "applied": False,
        "warning": "Confirmation does not apply anything. No write operation exists in this release.",
    }


def build_app(options: dict[str, Any]):
    token = options.get("mcp_auth_token", "")
    if not isinstance(token, str) or len(token) < 32:
        raise RuntimeError("Set mcp_auth_token in the add-on UI to a random value of at least 32 characters")
    ha_token = options.get("ha_token", "")
    if not isinstance(ha_token, str) or len(ha_token) < 20:
        raise RuntimeError("Set ha_token in the add-on UI; do not paste it into chat or place it in the archive")
    ha_base_url = options.get("ha_base_url", "http://homeassistant:8123")
    if not isinstance(ha_base_url, str) or not ha_base_url.startswith(("http://", "https://")) or any(ch in ha_base_url for ch in "?#@"):
        raise RuntimeError("ha_base_url must be a plain http(s) origin without credentials, query, or fragment")
    global HA_BASE_URL, HA_TOKEN
    HA_BASE_URL = ha_base_url.rstrip("/")
    HA_TOKEN = ha_token
    hosts = options.get("allowed_hosts", [])
    if not isinstance(hosts, list) or not hosts or not all(isinstance(h, str) and h for h in hosts):
        raise RuntimeError("allowed_hosts must be a non-empty list of host:port values")
    # Do not expose the server's unauthenticated default app; wrap all MCP routes.
    mcp_app = mcp.streamable_http_app()
    return Starlette(
        routes=mcp_app.routes,
        middleware=[Middleware(BearerAuthMiddleware, token=token, allowed_hosts={h.lower() for h in hosts})],
        lifespan=mcp_app.router.lifespan_context,
    )


def main() -> None:
    options = load_options()
    app = build_app(options)
    uvicorn.run(app, host="0.0.0.0", port=8099, log_level="info", access_log=False)


if __name__ == "__main__":
    main()
