# Hermes MCP server — Mazda MX-5 ND service manual search (stdio / SQLite FTS5)
{ lib, python312, python312Packages, writeShellScriptBin, src }:

let
  py = python312Packages;
  mcpSrc = lib.cleanSourceWith {
    src = src;
    filter = path: type:
      lib.any (prefix: lib.hasPrefix prefix (toString path)) [
        "/hermes-mcp/"
        "/manual/"
        "/flake.nix"
        "/nix/"
      ];
  };
  pyPkgs = with py; [
    mcp
    beautifulsoup4
    lxml
    anyio
    httpx
    pydantic
    starlette
    sse-starlette
    uvicorn
  ];
  pythonEnv = "${python312}/bin/python";
  pythonPath = lib.makeSearchPath python312.sitePackages pyPkgs;
in
{
  hermes-mcp = writeShellScriptBin "hermes-mcp" ''
    export PYTHONPATH="${pythonPath}"
    exec ${pythonEnv} ${mcpSrc}/hermes-mcp/server.py "$@"
  '';

  hermes-index-manual = writeShellScriptBin "hermes-index-manual" ''
    export PYTHONPATH="${pythonPath}"
    exec ${pythonEnv} ${mcpSrc}/hermes-mcp/index_manual.py "$@"
  '';
}