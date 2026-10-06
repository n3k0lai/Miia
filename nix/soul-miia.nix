# Seed the car identity from the public flake, then replace it with
# n3k0lai/soul branch miia when a key can read that private repo.
{ lib, pkgs, ... }:
let
  soulRev = "ac99aa21f3f8db1c5d14340b4f578d794608e379";
  seed = ../soul;
in
{
  systemd.services.miia-soul = {
    description = "Install soul branch miia, or the matching seed if the private repo is not readable yet";
    wantedBy = [ "multi-user.target" ];
    after = [ "network-online.target" ];
    wants = [ "network-online.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      User = "hermes";
      Group = "hermes";
    };
    script = ''
      set -eu
      ROOT=/var/lib/hermes/.hermes
      if [ -d "$ROOT/.git" ]; then
        exit 0
      fi
      install -d -m 0755 "$ROOT/memories"
      if [ ! -f "$ROOT/SOUL.md" ]; then
        install -m 0644 ${seed}/SOUL.md "$ROOT/SOUL.md"
        install -m 0644 ${seed}/AGENTS.md "$ROOT/AGENTS.md"
        install -m 0644 ${seed}/HEARTBEAT.md "$ROOT/HEARTBEAT.md"
        install -m 0644 ${seed}/memories/USER.md "$ROOT/memories/USER.md"
        printf '%s\n' ${lib.escapeShellArg soulRev} > "$ROOT/.soul-rev"
      fi
      tmp=$(mktemp -d)
      if ${pkgs.git}/bin/git clone --branch miia --depth 1 git@github.com:n3k0lai/soul.git "$tmp"; then
        branch=$(${pkgs.git}/bin/git -C "$tmp" rev-parse --abbrev-ref HEAD)
        if [ "$branch" = "miia" ]; then
          rm -rf "$ROOT"
          mv "$tmp" "$ROOT"
        else
          rm -rf "$tmp"
        fi
      else
        rm -rf "$tmp"
        exit 0
      fi
    '';
  };
}
