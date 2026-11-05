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
    version = "0.78.1";

    src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

    passthru = {
      sources = {
        aarch64-darwin = fetchurl {
          url = "https://downloads.cursor.com/sand/stable/darwin-arm64/${finalAttrs.version}/Grok_Bot_${finalAttrs.version}.dmg";
          hash = "sha256-Dldd/S9jiAjwSH+I3sa/U6hxysKTnef+RUmB+Sf58Nk=";
        };
        aarch64-linux = fetchurl {
          url = "https://downloads.cursor.com/grokbot/stable/72e130b4e6be3fdc47b97e809b6b420908ce2dd8/linux/arm64/Grok_Bot_0.78.1.AppImage";
          hash = "sha256-XJVTL2FOb6/CUl8uONim6q01Nz1iN2b6jmj1hDWoUeg=";
        };
        x86_64-linux = fetchurl {
          url = "https://downloads.cursor.com/grokbot/stable/72e130b4e6be3fdc47b97e809b6b420908ce2dd8/linux/x64/Grok_Bot_0.78.1.AppImage";
          hash = "sha256-BQ11I8bvoEYmYROuLjsfPOlAlVSSwrlS/T5pi2DXP7g=";
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
