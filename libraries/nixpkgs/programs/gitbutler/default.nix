{
  lib,
  stdenv,
  cacert,
  cargo-tauri,
  cmake,
  curl,
  dart-sass,
  desktop-file-utils,
  fetchFromGitHub,
  glib-networking,
  jq,
  libgit2,
  makeBinaryWrapper,
  moreutils,
  nix-update-script,
  nodejs,
  openssl,
  pkg-config,
  pnpm,
  pnpmConfigHook,
  fetchPnpmDeps,
  rust,
  rustPlatform,
  turbo,
  webkitgtk_4_1,
  wrapGAppsHook4,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "gitbutler";
  version = "0.19.1";

  src = fetchFromGitHub {
    owner = "gitbutlerapp";
    repo = "gitbutler";
    tag = "release/${finalAttrs.version}";
    hash = "sha256-ZCjlN8DF/l1v4AHk2CPB8VcaSuRLVIuOWPUfSn59LiE=";
  };

  # https://github.com/NixOS/nixpkgs/issues/359340
  cargoPatches = [ ./gix-from-crates-io.patch ];
  cargoHash = "sha256-xANj79+FNgocgb21dGN+DBseHiNkADN6wsFcQXagz7c=";

  pnpmDeps = fetchPnpmDeps {
    inherit (finalAttrs) pname version src;
    fetcherVersion = 2;
    hash = "sha256-IAsEzM9kmZWnh390CV7mOyOshVlESsyoNT0ZvdY03KY=";
  };

  postPatch = ''
    tauriConfRelease="crates/gitbutler-tauri/tauri.conf.release.json"
    jq '.
        | (.version = "${finalAttrs.version}")
        | (.bundle.createUpdaterArtifacts = false)
        | (.bundle.externalBin = ["gitbutler-git-setsid", "gitbutler-git-askpass"])
      ' "$tauriConfRelease" | sponge "$tauriConfRelease"

    substituteInPlace apps/desktop/src/lib/backend/tauri.ts \
      --replace-fail 'checkUpdate = tauriCheck;' 'checkUpdate = () => null;'
  '';

  nativeBuildInputs = [
    cacert
    cargo-tauri.hook
    cmake
    dart-sass
    jq
    moreutils
    nodejs
    pkg-config
    pnpm
    pnpmConfigHook
    turbo
    wrapGAppsHook4
  ]
  ++ lib.optional stdenv.hostPlatform.isDarwin makeBinaryWrapper
  ++ lib.optional stdenv.hostPlatform.isLinux desktop-file-utils;

  buildInputs = [
    libgit2
    openssl
  ]
  ++ lib.optional stdenv.hostPlatform.isDarwin curl
  ++ lib.optionals stdenv.hostPlatform.isLinux [
    glib-networking
    webkitgtk_4_1
  ];

  tauriBuildFlags = [
    "--config"
    "crates/gitbutler-tauri/tauri.conf.release.json"
  ];

  env = {
    TRIPLE_OVERRIDE = rust.envVars.rustHostPlatformSpec;
    COREPACK_ENABLE_STRICT = 0;
    RUSTFLAGS = "--cfg tokio_unstable";
    TUBRO_BINARY_PATH = lib.getExe turbo;
    TURBO_TELEMETRY_DISABLED = 1;
    OPENSSL_NO_VENDOR = true;
    LIBGIT2_NO_VENDOR = 1;
  };

  preBuild = ''
    substituteInPlace node_modules/.pnpm/sass-embedded@*/node_modules/sass-embedded/dist/lib/src/compiler-path.js \
      --replace-fail 'compilerCommand = (() => {' 'compilerCommand = (() => { return ["${lib.getExe dart-sass}"];'

    turbo run --filter @gitbutler/svelte-comment-injector build
    pnpm build:desktop -- --mode production
  '';

  dontWrapGApps = true;

  postInstall = ''
    cargo build --release --target ${rust.envVars.rustHostPlatformSpec} -p but
    install -Dm755 target/${rust.envVars.rustHostPlatformSpec}/release/but $out/bin/but
  ''
  + lib.optionalString stdenv.hostPlatform.isDarwin ''
    makeBinaryWrapper $out/Applications/GitButler.app/Contents/MacOS/gitbutler-tauri $out/bin/gitbutler-tauri \
      "''${gappsWrapperArgs[@]}"
  ''
  + lib.optionalString stdenv.hostPlatform.isLinux ''
    wrapGApp $out/bin/gitbutler-tauri
    desktop-file-edit \
      --set-comment "A Git client for simultaneous branches on top of your existing workflow." \
      --set-key="Keywords" --set-value="git;" \
      --set-key="StartupWMClass" --set-value="GitButler" \
      $out/share/applications/GitButler.desktop
  '';

  # Tests require git-sourced gix-testtools APIs not available on crates.io
  doCheck = false;

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "release/(.*)"
    ];
  };

  meta = {
    description = "Git client for simultaneous branches on top of your existing workflow";
    homepage = "https://gitbutler.com";
    changelog = "https://github.com/gitbutlerapp/gitbutler/releases/tag/release/${finalAttrs.version}";
    license = lib.licenses.fsl11Mit;
    maintainers = with lib.maintainers; [
      getchoo
      techknowlogick
    ];
    mainProgram = "gitbutler-tauri";
    platforms = lib.platforms.linux ++ lib.platforms.darwin;
  };
})
