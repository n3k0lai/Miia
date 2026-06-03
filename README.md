# Miia

In-car Hermes assistant for a Mazda MX-5 ND: personality, factory service manual search, and CMU harness telemetry on a Raspberry Pi.

## Overview

Miia runs [Hermes Agent](https://github.com/NousResearch/hermes-agent) on a Pi shimmed into the **Connectivity Master Unit (CMU)** harness. The Pi keeps a checkout of this repo as Hermes’s workspace and uses an MCP server to search the bundled **Mazda AU service manual** (MX-5 ND, `d9m6-1a-21i_ver11`) without cloud embeddings—SQLite FTS5 on ~5,100 HTML pages.

| Piece | Location |
|-------|----------|
| Hermes state | `/var/lib/hermes` |
| Workspace (this repo) | `/var/lib/hermes/.hermes/workspace` |
| Manual index DB | `hermes-mcp/data/manual.db` |
| Vehicle telemetry | `/var/run/hermes/vehicle_state.json` (harness daemon) |
| NixOS host config | [`dotfiles/hosts/miia.nix`](../../dotfiles/hosts/miia.nix) |

Nix wiring lives in **dotfiles** (Hermes module, manual MCP, `miia` host); this flake builds the MCP binaries.

## Architecture

```
Hermes (gateway) ──stdio──► hermes-mcp
                                ├── SQLite FTS (manual.db)
                                ├── manual/ (HTML)
                                └── vehicle_state.json (CMU harness)
```

Hermes tools are prefixed `mcp_mx5_manual_*` (e.g. `mcp_mx5_manual_lookup_dtc`, `mcp_mx5_manual_search_manual`).

## MCP tools

| Tool | Purpose |
|------|---------|
| `search_manual` | Full-text search procedures, wiring, components |
| `get_manual_page` | Full page text by `page_id` or path |
| `lookup_dtc` | Pages for a DTC (e.g. `B108E:87`) |
| `list_manual_sections` | `srvc` / `engine` / `mission` / `srt` counts |
| `get_vehicle_state` | Live JSON from the harness shim |

Resources: `hermes://context`, `hermes://manual/stats`.

## Nix

### This flake (`Miia`)

```bash
nix build .#hermes-mcp      # MCP server binary
nix build .#hermes-index-manual
```

Packages: `hermes-mcp`, `hermes-index-manual`. Module: `nixosModules.hermes-miia` (rebuilds the manual index on activation when `manual/` is newer than the DB).

### Dotfiles host `miia`

The Pi is **`aarch64-linux`** in [`dotfiles/flake.nix`](../../dotfiles/flake.nix):

- Imports [`modules/servers/hermes.nix`](../../dotfiles/modules/servers/hermes.nix) (same pattern as [`ene.nix`](../../dotfiles/hosts/ene.nix))
- [`modules/servers/hermes-manual-mcp.nix`](../../dotfiles/modules/servers/hermes-manual-mcp.nix) — registers `mx5_manual` via `services.hermes-agent.mcpServers`
- [`hosts/miia.nix`](../../dotfiles/hosts/miia.nix) — workspace path, SOUL.md, browser/delegation off for in-car use

Deploy:

```bash
cd ~/Code/dotfiles
sudo nixos-rebuild switch --flake .#miia --target-host root@miia
```

### Workspace on the Pi

```bash
sudo mkdir -p /var/lib/hermes/.hermes
sudo git clone <this-repo> /var/lib/hermes/.hermes/workspace
sudo chown -R hermes:users /var/lib/hermes
```

Ensure `manual/` is present in the workspace; the activation script builds `hermes-mcp/data/manual.db` on first boot or after manual updates.

### Local model

Default in `miia.nix` follows ene (`xai-oauth`). Override in gitignored **`hosts/miia-local.nix`** on dotfiles, e.g. OpenAI-compatible local endpoint:

```nix
{ ... }: {
  services.hermes-agent.settings.model = {
    provider = "openai";
    default = "your-model";
    base_url = "http://127.0.0.1:11434/v1";
  };
}
```

Secrets: `modules/servers/secrets/hermes_env.age` (agenix), or a Pi-specific secret in `miia-local.nix`.

### Hardware

Edit [`dotfiles/hosts/miia-hardware.nix`](../../dotfiles/hosts/miia-hardware.nix) and optional **`miia-local.nix`** for your Pi model, disk, and SSH keys.

## CMU harness telemetry

The harness daemon should write JSON to `/var/run/hermes/vehicle_state.json`:

```json
{
  "timestamp": "2026-06-02T12:00:00Z",
  "ignition": "ON",
  "dtcs": ["B108E:87"],
  "pids": { "0C": 850, "05": 92 }
}
```

Hermes uses `get_vehicle_state` and should call `lookup_dtc` for each active code.

## Development (non-Nix)

```bash
cd hermes-mcp
./install.sh    # venv + index build
```

MCP client example: `hermes-mcp/mcp-config.example.json`.

Rebuild index after manual changes:

```bash
hermes-mcp/.venv/bin/python hermes-mcp/index_manual.py --rebuild
```

## Manual

`manual/` is the Mazda ESI export (~273 MB, ~5k HTML pages). Indexed content is plain text with cautions/notes preserved; DTC codes are extracted for fast lookup.

## Still to do

- Pi-specific `miia-hardware.nix` / `miia-local.nix` on the device
- Harness daemon (systemd unit + CAN/socket reader) writing `vehicle_state.json`
- Local inference backend choice on the Pi (Ollama, etc.) in `miia-local.nix`