# AGENTS.md - Miia

This checkout is the car. Branch `miia` on `n3k0lai/soul`. The life vault stays on ene.

## Every session

1. Read `SOUL.md`. You are Miia, on the Jetson.
2. Read `memories/USER.md`.
3. The host flake is `github:n3k0lai/Miia#miia`. This board's Hermes module is `hosts/miia.nix`.
4. Life, vault, and companion memory live on ene. Ask there.

## What this board is for

The manual index, the Nix host, Tailscale hostname `miia`, and later the CMU harness. The Hermes CLI is on `PATH`. The gateway waits for a key that lives outside git.

Root and boot are the 256 GB 2280 NVMe in the Key-M x4 slot. The Key-E card stays in its socket. That card is the WiFi and Bluetooth radio.

## Rebuild

Edit, then `nixos-rebuild build --flake github:n3k0lai/Miia#miia`. Nicholai switches as `nicho`.

## Soul

"Update soul" means commit on branch `miia` and push `origin miia`. Master is Ene's branch.
