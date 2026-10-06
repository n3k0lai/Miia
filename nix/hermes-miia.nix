# Miia car host helpers — manual index activation (import from dotfiles miia.nix)
{ config, lib, pkgs, hermesMcpPackage ? null, ... }:

let
  cfg = config.hermes.miia;
  mcpPkg = if hermesMcpPackage != null then hermesMcpPackage else null;
in
{
  options.hermes.miia = {
    enable = lib.mkEnableOption "Miia in-car workspace (manual index, vehicle state paths)";
    workspace = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/hermes/.hermes/workspace";
      description = "Miia git checkout (Hermes working directory on the Jetson)";
    };
    vehicleStateFile = lib.mkOption {
      type = lib.types.str;
      default = "/var/run/hermes/vehicle_state.json";
      description = "JSON telemetry from the CMU harness shim";
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.tmpfiles.rules = [
      "d /var/run/hermes 0755 hermes users - -"
    ];

    system.activationScripts.hermes-miia-manual-index = lib.stringAfter [ "hermes-agent-setup" ] ''
      WORKSPACE="${cfg.workspace}"
      MANUAL="$WORKSPACE/manual"
      DB="$WORKSPACE/hermes-mcp/data/manual.db"
      if [ ! -d "$MANUAL" ]; then
        echo "hermes-miia: manual/ not found in workspace, skipping index"
        exit 0
      fi

      NEED_INDEX=0
      if [ ! -f "$DB" ]; then
        NEED_INDEX=1
      elif [ "$MANUAL" -nt "$DB" ]; then
        NEED_INDEX=1
      fi

      if [ "$NEED_INDEX" = "1" ]; then
        echo "hermes-miia: building manual search index..."
        mkdir -p "$(dirname "$DB")"
        chown hermes:users "$(dirname "$DB")" 2>/dev/null || true
        ${mcpPkg}/bin/hermes-index-manual \
          --manual-root "$MANUAL" \
          --db "$DB" \
          --rebuild
        chown -R hermes:users "$(dirname "$DB")" 2>/dev/null || true
        chmod -R g+rw "$(dirname "$DB")" 2>/dev/null || true
      fi
    '';
  };
}