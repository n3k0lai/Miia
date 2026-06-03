{
  description = "Miia — in-car Hermes workspace (MX-5 ND manual, CMU harness telemetry)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
  };

  outputs = { self, nixpkgs }:
    let
      forAllSystems = nixpkgs.lib.genAttrs [ "aarch64-linux" "x86_64-linux" ];
    in {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in let
          mcp = pkgs.callPackage ./nix/hermes-mcp.nix { src = self; };
        in {
          inherit (mcp) hermes-mcp hermes-index-manual;
          default = mcp.hermes-mcp;
        });

      nixosModules.hermes-miia = ./nix/hermes-miia.nix;
    };
}