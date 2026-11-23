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
        in
        {
          default = (pkgs.mkShell.override { stdenv = pkgs.gccStdenv; }) {
            packages = [
              pkgs.git
              pkgs.meson
              pkgs.ninja
              pkgs.pkg-config
              pkgs.python3 # Used by the optional clangd setup script.
            ] ++ pkgs.lib.optionals pkgs.stdenv.hostPlatform.isLinux [ pkgs.valgrind ];

            dontUseMesonConfigure = true;
          };
        });
    };
}
