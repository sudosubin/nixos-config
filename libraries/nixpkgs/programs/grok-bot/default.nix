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
    version = "1.2.3";

    src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

    passthru = {
      sources = {
        aarch64-darwin = fetchurl {
          url = "https://downloads.cursor.com/sand/stable/darwin-arm64/${finalAttrs.version}/Grok_Bot_${finalAttrs.version}.dmg";
          hash = "sha256-t8YmjUC/krQ7by7d1zPk1bXTbiKdIgHQYpihmw5i2gg=";
        };
        aarch64-linux = fetchurl {
          url = "https://downloads.cursor.com/grokbot/stable/a5927fa2ba82336a29f9343babd28b4c903abbb2/linux/arm64/Grok_Bot_1.2.3.AppImage";
          hash = "sha256-CPE4E62WHVozEc1MGfipuAEBBc1swFoL3KSkJYPhSac=";
        };
        x86_64-linux = fetchurl {
          url = "https://downloads.cursor.com/grokbot/stable/a5927fa2ba82336a29f9343babd28b4c903abbb2/linux/x64/Grok_Bot_1.2.3.AppImage";
          hash = "sha256-XgG0HTXYigmabcHi5V8VVHP4HZCdjV8Yx6HSghkScPA=";
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
