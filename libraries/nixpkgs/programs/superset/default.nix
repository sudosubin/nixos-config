{
  appimageTools,
  fetchurl,
  gh,
  gitMinimal,
  lib,
  makeWrapper,
  stdenvNoCC,
  unzip,
}:
let
  runtimePath = lib.makeBinPath [
    gh
    gitMinimal
  ];

in
stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "superset";
  version = "1.5.0";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  dontBuild = true;
  dontUnpack = stdenvNoCC.hostPlatform.isLinux;
  sourceRoot = ".";

  nativeBuildInputs = lib.optionals stdenvNoCC.hostPlatform.isDarwin [
    makeWrapper
    unzip
  ];

  installPhase = ''
    runHook preInstall
  ''
  + lib.optionalString stdenvNoCC.hostPlatform.isDarwin ''
    mkdir -p $out/{Applications,bin}
    cp -R Superset.app $out/Applications/

    makeWrapper "$out/Applications/Superset.app/Contents/MacOS/Superset" \
      "$out/bin/${finalAttrs.pname}" \
      --suffix PATH : ${runtimePath}
  ''
  + lib.optionalString stdenvNoCC.hostPlatform.isLinux (
    let
      appimageContents = appimageTools.extractType2 {
        inherit (finalAttrs) pname version src;
      };

      package = appimageTools.wrapType2 {
        inherit (finalAttrs)
          pname
          version
          src
          meta
          ;

        extraPkgs =
          pkgs: with pkgs; [
            libappindicator-gtk3
            libsecret
          ];

        extraInstallCommands = ''
          install -Dm444 ${appimageContents}/@supersetdesktop.desktop \
            $out/share/applications/superset.desktop
          substituteInPlace $out/share/applications/superset.desktop \
            --replace-fail 'Exec=AppRun' 'Exec=${finalAttrs.pname}'

          install -Dm444 ${appimageContents}/@supersetdesktop.png \
            $out/share/icons/hicolor/512x512/apps/@supersetdesktop.png

          source "${makeWrapper}/nix-support/setup-hook"
          wrapProgram "$out/bin/${finalAttrs.pname}" \
            --suffix PATH : ${runtimePath} \
            --add-flags "''${NIXOS_OZONE_WL:+''${WAYLAND_DISPLAY:+--ozone-platform-hint=auto --enable-features=WaylandWindowDecorations}}"
        '';
      };
    in
    ''
      mkdir -p $out
      cp -a ${package}/. $out/
    ''
  )
  + ''
    runHook postInstall
  '';

  passthru = {
    sources = {
      x86_64-linux = fetchurl {
        url = "https://github.com/superset-sh/superset/releases/download/desktop-v${finalAttrs.version}/Superset-x86_64.AppImage";
        hash = "sha256-VlFEEOmdTEGstZz0UFQdd6QLmkdg9zU8rjapf/RNkXE=";
      };
      aarch64-darwin = fetchurl {
        url = "https://github.com/superset-sh/superset/releases/download/desktop-v${finalAttrs.version}/Superset-arm64-mac.zip";
        hash = "sha256-IsJPEANJlq30hPDJW9w65p6wYWOm0PoSgi0QOkzQ8UE=";
      };
      x86_64-darwin = fetchurl {
        url = "https://github.com/superset-sh/superset/releases/download/desktop-v${finalAttrs.version}/Superset-x64-mac.zip";
        hash = "sha256-zVqZbB5KkERRH84qTBLgHc0ETL1KE0lhFRjI4n3mFJg=";
      };
    };
    updateScript = ./update.sh;
  };

  meta = {
    description = "Terminal for orchestrating agents";
    homepage = "https://superset.sh";
    changelog = "https://github.com/superset-sh/superset/releases/tag/desktop-v${finalAttrs.version}";
    license = lib.licenses.elastic20;
    mainProgram = finalAttrs.pname;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = builtins.attrNames finalAttrs.passthru.sources;
    sourceProvenance = with lib.sourceTypes; [ binaryNativeCode ];
  };
})
