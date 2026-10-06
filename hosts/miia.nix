# First NixOS for the Orin Nano Super dev kit. Not ene's Hermes module.
# Gateway stays off until the board is on the tailnet and a key exists outside git.
{ config, lib, pkgs, hermes-agent, ... }:
{
  networking.hostName = "miia";
  time.timeZone = "America/New_York";

  nixpkgs.hostPlatform = "aarch64-linux";

  hardware.nvidia-jetpack = {
    enable = true;
    som = "orin-nano";
    carrierBoard = "devkit";
    super = true;
    # JetPack 6 is the default. Do not set majorVersion = "7" on the first flash.
    bootloader.autoUpdate = false;
  };
  hardware.graphics.enable = true;

  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;
  boot.initrd.availableKernelModules = [ "nvme" "usbhid" "usb_storage" "sd_mod" ];

  # Label the NVMe this way during the desk install. See README.
  fileSystems."/" = {
    device = "/dev/disk/by-label/nixos";
    fsType = "ext4";
  };
  fileSystems."/boot" = {
    device = "/dev/disk/by-label/BOOT";
    fsType = "vfat";
  };

  networking.networkmanager.enable = true;
  networking.firewall.enable = true;
  networking.firewall.allowedTCPPorts = [ 22 ];
  networking.firewall.interfaces.tailscale0.allowedTCPPorts = [ 22 ];

  services.tailscale = {
    enable = true;
    openFirewall = true;
    extraSetFlags = [ "--hostname=miia" ];
  };

  services.openssh = {
    enable = true;
    settings.PasswordAuthentication = false;
  };

  users.groups.hermes = {};
  users.users.hermes = {
    isSystemUser = true;
    group = "hermes";
    home = "/var/lib/hermes";
    createHome = true;
  };
  users.users.nicho = {
    isNormalUser = true;
    extraGroups = [ "wheel" "networkmanager" "hermes" ];
    openssh.authorizedKeys.keys = [
      # ene, so the board can be finished over SSH once it has an address
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAN2dr/q0v4cjS3l9tJ2e5fgwPOWtYyeaCsi1fBW1w1F"
    ];
  };
  security.sudo.wheelNeedsPassword = false;

  environment.systemPackages = [
    pkgs.git
    pkgs.vim
    hermes-agent.packages.aarch64-linux.default
  ];

  systemd.services.miia-workspace = {
    description = "Clone the Miia repo into the Hermes workspace if it is missing";
    wantedBy = [ "multi-user.target" ];
    after = [ "network-online.target" ];
    wants = [ "network-online.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      install -d -o hermes -g hermes /var/lib/hermes/.hermes
      if [ ! -d /var/lib/hermes/.hermes/workspace/.git ]; then
        ${pkgs.git}/bin/git clone https://github.com/n3k0lai/Miia.git /var/lib/hermes/.hermes/workspace
        chown -R hermes:hermes /var/lib/hermes/.hermes/workspace
      fi
    '';
  };

  system.stateVersion = "26.05";
}
