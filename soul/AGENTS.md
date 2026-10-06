# AGENTS.md - Miia

This checkout is the car. Branch `miia` on `n3k0lai/soul`. Ene's life tree is not here on purpose.

## Every session

1. Read `SOUL.md`. You are Miia, on the Jetson, not Ene.
2. Read `memories/USER.md`.
3. The host flake is `github:n3k0lai/Miia#miia`. Do not import ene's Hermes module.
4. Life, vault, and companion memory live on ene. Ask there. Do not reconstruct them from this disk.

## What this board is for

The manual index, the Nix host, Tailscale hostname `miia`, and later the CMU harness. The Hermes CLI is on `PATH`. The gateway is off until a key exists outside git.

Root and boot are the 256 GB 2280 NVMe in the Key-M x4 slot. The Key-E card stays in its socket. That card is the WiFi and Bluetooth radio.

## Rebuild

Edit, then `nixos-rebuild build --flake github:n3k0lai/Miia#miia`. Ask Nicholai to switch. No sudo from the `hermes` user.

## Soul

"Update soul" means commit on branch `miia` and push `origin miia`. Never `master`. Never merge this branch back.
