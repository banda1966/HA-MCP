# Home Assistant MCP Dashboard Connector — local repository

This is a **source repository template** for a custom Home Assistant OS add-on. It is not a prebuilt or signed image.

## Install

1. Put this repository in a Git repository reachable by your Home Assistant instance, and set `url` in `repository.yaml` to that repository's URL. Or use a local add-on repository directory supported by your HA OS setup.
2. In Home Assistant, open **Settings → Apps → App store → ⋮ → Repositories**, add the repository URL and refresh.
3. Install **Home Assistant MCP Dashboard Connector**.
4. In add-on options, set `mcp_auth_token` to a randomly generated value of at least 32 characters and `ha_token` to a Home Assistant long-lived access token. Do this only in the local HA UI, never in chat or in this archive. The values are stored in Supervisor add-on options and must be protected with admin access and backups.
5. Set `allowed_hosts` to the exact `host:8099` sent by your local MCP client. Default examples may need to be replaced with the Home Assistant hostname/IP you use.
6. Start the add-on. Test `http://<HA-IP>:8099/health`. Configure your native/local MCP client for `http://<HA-IP>:8099/mcp` with `Authorization: Bearer <MCP token>` and no `Origin` header.

## Scope and limitations

- Python MCP server using Streamable HTTP.
- Read-only Home Assistant API helper (`GET` only) and limited entity lookup.
- Static Lovelace YAML validation.
- Proposal/confirmation prototype: exact target+diff, one use, five-minute expiry.
- **No dashboard write tool exists** in this release. Confirmation cannot apply anything.
- A LAN-only endpoint is not reachable from ChatGPT cloud without a separate supported connection path. No tunnel is included.
- Do not port-forward port 8099 or expose the endpoint to the public internet.

## Tests

```sh
cd ha_mcp_dashboard_connector
python -m unittest discover -s tests -v
```

These are local unit tests only; they do not replace a Supervisor build/install test on the target architecture.
