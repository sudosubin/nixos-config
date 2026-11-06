{
  appimageTools,
  fetchurl,
  lib,
  makeWrapper,
  stdenvNoCC,
  _7zz,
}:

let
  mkDerivation =
    if stdenvNoCC.hostPlatform.isDarwin then stdenvNoCC.mkDerivation else appimageTools.wrapType2;
in
mkDerivation (
  finalAttrs:
  {
    pname = "grok-bot";
    version = "0.79.2";

    src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

    passthru = {
      sources = {
        aarch64-darwin = fetchurl {
          url = "https://downloads.cursor.com/sand/stable/darwin-arm64/${finalAttrs.version}/Grok_Bot_${finalAttrs.version}.dmg";
          hash = "sha256-YNRBBon15r3VKLNe4gljIWjSwUM+Xfzq8OnWAwCZryA=";
        };
        aarch64-linux = fetchurl {
          url = "https://downloads.cursor.com/grokbot/stable/676f0815a4013954f4c8e3f4ac413acfbac0376c/linux/arm64/Grok_Bot_0.79.2.AppImage";
          hash = "sha256-5ZxuT/mfW2ujES18zlvnqrONMINa1sTOsekqM49D3y8=";
        };
        x86_64-linux = fetchurl {
          url = "https://downloads.cursor.com/grokbot/stable/676f0815a4013954f4c8e3f4ac413acfbac0376c/linux/x64/Grok_Bot_0.79.2.AppImage";
          hash = "sha256-7VIYEcV66qxPMwM2YUSNpJ392fLD+KAatX8rv5JicG4=";
        };
      };
      updateScript = ./update.sh;
    };

    meta = {
      description = "AI teammates that work across your apps and tools";
      homepage = "https://x.ai/bot";
      license = lib.licenses.unfree;
      maintainers = with lib.maintainers; [ sudosubin ];
      mainProgram = "grok-bot";
      platforms = builtins.attrNames finalAttrs.passthru.sources;
      sourceProvenance = [ lib.sourceTypes.binaryNativeCode ];
    };
  }
  // lib.optionalAttrs stdenvNoCC.hostPlatform.isDarwin {
    sourceRoot = ".";
    nativeBuildInputs = [
      _7zz
      makeWrapper
    ];

    dontFixup = true;

    installPhase = ''
      runHook preInstall

      mkdir -p "$out/Applications" "$out/bin"
      cp -R "Grok Bot.app" "$out/Applications/"
      makeWrapper "$out/Applications/Grok Bot.app/Contents/MacOS/Grok Bot" "$out/bin/grok-bot"

      runHook postInstall
    '';
  }
  // lib.optionalAttrs stdenvNoCC.hostPlatform.isLinux {
    extraInstallCommands =
      let
        contents = appimageTools.extract { inherit (finalAttrs) pname version src; };
      in
      ''
        install -Dm644 ${contents}/grok-bot.desktop "$out/share/applications/grok-bot.desktop"
        substituteInPlace "$out/share/applications/grok-bot.desktop" \
          --replace-fail 'Exec=AppRun' "Exec=$out/bin/grok-bot"
        cp -r ${contents}/usr/share/icons "$out/share/icons"
      '';
  }
)
