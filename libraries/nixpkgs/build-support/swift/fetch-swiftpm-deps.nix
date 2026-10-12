{
  lib,
  stdenv,
  cacert,
  gitMinimal,
  jq,
  swift,
  swiftpm,
  unzip,
}:

# Resolves Package.resolved with SwiftPM into a fixed-output derivation laid
# out like swiftpm2nix's output, for swiftpmUnpackHook
{
  pname,
  hash ? lib.fakeHash,
  swiftpmManifest ? null,
  swiftpmResolved ? "Package.resolved",
  ...
}@args:

stdenv.mkDerivation (
  removeAttrs args [
    "hash"
    "swiftpmManifest"
    "swiftpmResolved"
  ]
  // {
    pname = "${pname}-swiftpm-deps";

    nativeBuildInputs = [
      cacert
      gitMinimal
      jq
      swift
      swiftpm
      unzip
    ];

    postPatch =
      lib.optionalString (swiftpmManifest != null) ''
        cp ${swiftpmManifest} Package.swift
      ''
      + lib.optionalString (swiftpmResolved != "Package.resolved") ''
        cp ${lib.escapeShellArg swiftpmResolved} Package.resolved
      '';

    buildPhase = ''
      runHook preBuild
      export HOME="$TMPDIR"
      swift package resolve --disable-sandbox --force-resolved-versions
      runHook postBuild
    '';

    installPhase = ''
      runHook preInstall
      cd .build

      # Keep top-level files and the directories of non-test targets, dropping
      # tests, docs and unused submodules
      for subpath in $(jq -r '.object.dependencies[].subpath' workspace-state.json); do
        mkdir -p "$out/Packages/$subpath"
        find "checkouts/$subpath" -mindepth 1 -maxdepth 1 ! -type d -exec cp --update=none -t "$out/Packages/$subpath" {} +
        for dir in $(swift package dump-package --disable-sandbox --package-path "checkouts/$subpath" | jq -r '
          [.targets[] | select(.type != "test" and .url == null)
            | .path // if .type == "plugin" then "Plugins" else "Sources Source src srcs" end
            | split("/")[0]] | unique[]
        '); do
          if [[ -e "checkouts/$subpath/$dir" ]]; then
            cp -r --update=none "checkouts/$subpath/$dir" "$out/Packages/$subpath/"
          fi
        done
      done

      # Edit mode is how swiftpmUnpackHook vendors dependencies
      jq --sort-keys --arg build "$PWD/" '
        .object.dependencies[].state = { name: "edited", path: null }
        | .object.artifacts[].path |= ltrimstr($build)
      ' workspace-state.json > "$out/workspace-state.json"
      jq -r '.object.artifacts[].path' "$out/workspace-state.json" | xargs -r cp -r --parents -t "$out"

      find "$out" -name .git -prune -exec rm -rf {} +
      runHook postInstall
    '';

    dontFixup = true;

    impureEnvVars = lib.fetchers.proxyImpureEnvVars;
    outputHashMode = "recursive";
    outputHash = hash;
  }
)
