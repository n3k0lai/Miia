{
  description = "Miia — Jetson Orin Nano Super in the MX-5, NixOS host plus the manual MCP";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

    jetpack.url = "github:anduril/jetpack-nixos";
    jetpack.inputs.nixpkgs.follows = "nixpkgs";

    # Same pin the fleet uses. Do not follow nixpkgs: this flake tracks unstable.
    hermes-agent.url = "github:NousResearch/hermes-agent/v2026.9.24";
  };

  outputs = { self, nixpkgs, jetpack, hermes-agent }:
    let
      forAllSystems = nixpkgs.lib.genAttrs [ "aarch64-linux" "x86_64-linux" ];
    in {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          mcp = pkgs.callPackage ./nix/hermes-mcp.nix { src = self; };
        in {
          inherit (mcp) hermes-mcp hermes-index-manual;
          default = mcp.hermes-mcp;
        });

      nixosModules.hermes-miia = ./nix/hermes-miia.nix;

      nixosConfigurations.miia = nixpkgs.lib.nixosSystem {
        system = "aarch64-linux";
        specialArgs = { inherit hermes-agent; };
        modules = [
          jetpack.nixosModules.default
          ./hosts/miia.nix
          ./nix/soul-miia.nix
          {
            nixpkgs.config = {
              allowUnfree = true;
              cudaSupport = true;
              cudaCapabilities = [ "8.7" ];
            };
          }
        ];
      };
    };
}
