# Miia

In-car computer for a 2018 Mazda MX-5 ND Club. The board is a Jetson Orin Nano Super Developer Kit in the cluster void. The CMU stays in the dash. This repo is the NixOS host and the manual-search MCP. The Raspberry Pi shim plan is retired.

The heavy conversation stays on ene. This board is a Tailscale node that can pull this repo and keep working once it is on the tailnet. Its identity is `n3k0lai/soul` branch `miia` at `672360fc018468bd122382c9e2deb5c0e02f8ab2`. That repo is private, so the desk install carries the same files under `soul/` and writes them to `/var/lib/hermes/.hermes` on first boot. When the board has a key that can read the private repo, that seed is replaced by a checkout of branch `miia`.

## What is on the board

NixOS 26.05, aarch64, JetPack 6, `som = "orin-nano"`, `super = true`. Tailscale hostname `miia`. Hermes CLI from `NousResearch/hermes-agent` at `v2026.9.24`. The Hermes gateway is not started. It does not share ene's Discord session, and it does not get a model key from this repo.

Root disk is the 256 GB 2280 NVMe in the Key-M x4 slot. Screw that in before the first boot. Do not install onto the microSD.

Firmware flash still comes from kiss, which is x86_64. The flash package is `github:anduril/jetpack-nixos#flash-orin-nano-super-devkit`. This repo does not vendor that script.

## Desk install

Seat the NVMe. Hold recovery, tap reset, and confirm `lsusb` shows `0955:7023`.

On kiss, build and run the firmware flash:

```bash
nix build github:anduril/jetpack-nixos#flash-orin-nano-super-devkit
sudo ./result/bin/flash-orin-nano-super-devkit
```

Then build the installer ISO and write it to a USB stick, not to the NVMe:

```bash
nix build github:anduril/jetpack-nixos#iso_minimal
```

Boot that stick from the UEFI menu. Partition the NVMe with labels `BOOT` (vfat, the ESP) and `nixos` (ext4). Install with:

```bash
sudo nixos-install --flake github:n3k0lai/Miia#miia
```

Reboot from the NVMe. On the board:

```bash
sudo tailscale up --ssh --hostname=miia
```

From ene, once `miia` shows on the tailnet, SSH as `nicho` and continue. The workspace clone lands at `/var/lib/hermes/.hermes/workspace` after the network is up. `hermes` is on `PATH` after that install. Turning the gateway on is a later switch, after a key exists outside this repo.

## MCP

`nix build .#hermes-mcp` still builds the manual search server. The HTML manual is not in this repo. The index is built on the board when `manual/` is present. Module: `nixosModules.hermes-miia`.

Tools stay `search_manual`, `get_manual_page`, `lookup_dtc`, `list_manual_sections`, and `get_vehicle_state`. The harness JSON path is still `/var/run/hermes/vehicle_state.json`. That daemon is not part of the first boot.

## What this host is not

It does not import the ene Hermes module. It does not open a second Discord bot. It does not fetch mazdatweaks.com. UART to the CMU is a later harness job, not part of the first boot.
