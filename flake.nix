{
  description = "DML development environment (Meson remains the build system)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = { self, nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          # check.sh uses gcov, so use GCC even where Clang is the default.
          stdenv = pkgs.gccStdenv;
          # Expose gcov without putting unwrapped gcc ahead of the Nix wrapper.
          gcov = pkgs.runCommand "gcov-${stdenv.cc.cc.version}" { } ''
            mkdir -p "$out/bin"
            ln -s ${stdenv.cc.cc}/bin/gcov "$out/bin/gcov"
          '';
          # GCC's ARM64 vectorized string scans produce Memcheck definedness
          # false positives in CPython. Change only this interpreter's build;
          # the default shell and DML's compiler flags remain untouched.
          valgrindPython = if system == "aarch64-linux" then
            pkgs.python312.override {
              self = valgrindPython;
              stdenv = pkgs.withCFlags [ "-fno-tree-loop-vectorize" ] pkgs.stdenv;
            }
          else pkgs.python312;
          mkDevShell = interpreter:
            (pkgs.mkShell.override { inherit stdenv; }) {
              name = "dml-dev";
              packages = [
                gcov
                pkgs.binutils
                pkgs.duckdb
                pkgs.git
                pkgs.lcov
                (pkgs.meson.override { python3 = interpreter; })
                pkgs.ninja
                pkgs.pkg-config
                (interpreter.withPackages (ps: [
                  ps.coverage
                  ps.hypothesis
                  ps.pytest
                  ps.pytest-cov
                  ps.pytest-xdist
                  ps.psutil
                ]))
              ] ++ pkgs.lib.optionals stdenv.hostPlatform.isLinux [ pkgs.valgrind ];

              # Entering the shell must not configure a build or change directories.
              dontUseMesonConfigure = true;
            };
        in
        {
          # Match CI's interpreter without requiring a custom Python build.
          default = mkDevShell pkgs.python312;
        } // pkgs.lib.optionalAttrs stdenv.hostPlatform.isLinux {
          valgrind = mkDevShell valgrindPython;
        });

      checks = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        pkgs.lib.optionalAttrs pkgs.stdenv.hostPlatform.isLinux {
          valgrind-python = pkgs.runCommandCC "dml-valgrind-python-check" {
            nativeBuildInputs = self.devShells.${system}.valgrind.nativeBuildInputs;
          } ''
            export PYTHONMALLOC=malloc
            valgrind --trace-children=yes --error-exitcode=101 \
              --leak-check=full --show-leak-kinds=definite \
              --errors-for-leak-kinds=definite --track-origins=yes \
              --suppressions=${./tests/valgrind-cpython.supp} \
              python3 ${./tests/nix/valgrind_runtime.py}

            # A real uninitialised read must still fail; do not merely test silence.
            "$CC" -O0 -g ${./tests/nix/uninitialized.c} -o negative-control
            status=0
            valgrind --error-exitcode=101 --track-origins=yes \
              ./negative-control > negative-control.log 2>&1 || status=$?
            if [ "$status" -ne 101 ]; then
              cat negative-control.log
              echo "error: Valgrind negative control exited $status, expected 101" >&2
              exit 1
            fi
            grep -F 'Conditional jump or move depends on uninitialised value(s)' negative-control.log
            mkdir "$out"
            cp negative-control.log "$out/"
          '';
        });
    };
}
