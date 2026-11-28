{
  description = "DML C core development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = { nixpkgs, ... }:
    {
      devShells = nixpkgs.lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ] (system:
        let
          pkgs = import nixpkgs { inherit system; };

          # Replay uses the TypeScript backend, so it needs neither Rust nor Apalache.
          quintCli = pkgs.buildNpmPackage rec {
            pname = "quint-cli";
            version = "0.33.1";
            src = pkgs.fetchFromGitHub {
              owner = "quint-co";
              repo = "quint";
              tag = "v${version}";
              hash = "sha256-F0Yj9e+qTOlj6RzspvkEhilXC6pFHvISBRLgvJmon7I=";
            };
            sourceRoot = "${src.name}/quint";
            npmDepsHash = "sha256-Bk21CfCh1xsY1cIYnSQfxxcpVkRbBg5EfGbFvJlTcvE=";
            npmBuildScript = "compile";
            npmFlags = [ "--ignore-scripts" ];
          };

          mkDevShell = extraPackages: (pkgs.mkShell.override { stdenv = pkgs.gccStdenv; }) {
            packages = [
              pkgs.git
              pkgs.meson
              pkgs.ninja
              pkgs.pkg-config
              pkgs.python3 # Used by the optional clangd setup script.
            ] ++ pkgs.lib.optionals pkgs.stdenv.hostPlatform.isLinux [ pkgs.valgrind ] ++ extraPackages;

            dontUseMesonConfigure = true;
          };
        in
        {
          default = mkDevShell [ ];
          quint = mkDevShell [ quintCli pkgs.nodejs ];
        });
    };
}
