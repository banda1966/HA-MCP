# Home Assistant MCP Dashboard Connector — local add-on source

Python-based development MVP for Home Assistant OS. It runs an authenticated MCP Streamable HTTP endpoint on port 8099 and provides:

- `connector_status`: checks whether the configured Home Assistant API is reachable
- `list_entities`: read-only entity lookup with basic filtering and limited output fields
- `validate_dashboard_yaml`: static YAML parsing/checks; does not apply YAML
- `create_write_proposal`: creates a proposal only
- `confirm_write_proposal`: records confirmation for the exact target and diff, single-use, 5-minute expiry

**No dashboard write operation is included.** The API helper implements GET only. Dashboard listing/updating varies by dashboard mode and is deliberately not guessed in this first version.

## Security notes

- Configure both `mcp_auth_token` and `ha_token` in the add-on's local Options UI. Use random values of at least 32 characters for the MCP token and a valid Home Assistant long-lived access token for `ha_token`.
- Never send either token in chat or include it in an archive/repository. The HA token is stored in the add-on's local options by Supervisor; restrict administrator access and protect backups.
- The default `ha_base_url` is `http://homeassistant:8123`, the usual internal service hostname. Change only if your setup requires it.
- Add the exact hostname:port used by the MCP client to `allowed_hosts`. Defaults are examples only.
- The endpoint is exposed on the LAN port 8099. Do not port-forward it or expose it directly to the internet. Use a firewall to restrict access to trusted LAN clients.
- Requests with an `Origin` header are rejected. Use a native/local MCP client that sends `Authorization: Bearer ...` and no `Origin` header.
- `/health` reveals only generic liveness and has no authentication.
- This add-on is not automatically reachable from ChatGPT cloud. No tunnel is included.

## Install as a local add-on repository

1. Copy this folder to a Git repository reachable from Home Assistant, or put it in a local add-on repository directory accessible to Supervisor.
2. In **Settings → Apps → App store → ⋮ → Repositories**, add the repository URL if using Git. Refresh and install **Home Assistant MCP Dashboard Connector**.
3. In the add-on's Configuration/Options, set `mcp_auth_token` and `ha_token` locally. Do not paste either token into ChatGPT. Set `allowed_hosts` to the exact `host:8099` value the local MCP client will send.
4. Start the add-on and inspect logs for startup errors. Test `http://<HA-IP>:8099/health` from the LAN.
5. Configure a local MCP client to connect to `http://<HA-IP>:8099/mcp` with `Authorization: Bearer <your local MCP token>` and no `Origin` header.

The Dockerfile is a source-build template. Build and test it on the target architecture before long-term use. This archive is source, not a prebuilt, signed add-on image. The Python SDK is pinned to the v1.x line for the current FastMCP API used by this MVP.

## Development tests

From this directory run:

```sh
python -m unittest discover -s tests -v
```

Tests exercise static YAML validation and the confirmation prototype. They do not test a live Home Assistant instance, MCP network transport, or the full Supervisor build/install path.
