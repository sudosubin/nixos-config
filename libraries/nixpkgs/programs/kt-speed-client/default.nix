{
  cpio,
  fetchurl,
  gzip,
  jdk8_headless,
  lib,
  makeWrapper,
  stdenvNoCC,
  xar,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "kt-speed-client";
  version = "3.0.5";

  src = fetchurl {
    url = "https://speed.kt.com/file/ktspeed.pkg";
    hash = "sha256-fA6Jpf9Ahp+Bcs4I1o9SIkbwDTCUr6MVQr2yutqanVU=";
  };

  nativeBuildInputs = [
    cpio
    gzip
    makeWrapper
    xar
  ];

  dontPatchShebangs = true;

  unpackPhase = ''
    runHook preUnpack

    xar -xf "$src"

    mkdir -p source
    cd source
    gzip -dc ../Payload | cpio -id

    runHook postUnpack
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p "$out/bin" "$out/libexec/${finalAttrs.pname}" "$out/share/${finalAttrs.pname}"

    cp Library/KTSpeedClient/kt-speed-client.jar "$out/libexec/${finalAttrs.pname}/"
    cp Library/KTSpeedClient/run.sh "$out/share/${finalAttrs.pname}/original-run.sh"
    cp Library/LaunchDaemons/com.kt.speed.client.plist "$out/share/${finalAttrs.pname}/"

    makeWrapper ${lib.getExe' jdk8_headless "java"} "$out/bin/${finalAttrs.pname}" \
      --run "cd $out/libexec/${finalAttrs.pname}" \
      --add-flags '-Dsun.misc.URLClassPath.disableJarChecking=true' \
      --add-flags "-jar $out/libexec/${finalAttrs.pname}/kt-speed-client.jar"

    runHook postInstall
  '';

  passthru.updateScript = ./update.sh;

  meta = {
    description = "KT 인터넷 속도 측정을 위한 로컬 백엔드 서비스";
    homepage = "https://speed.kt.com/";
    license = lib.licenses.unfree;
    mainProgram = finalAttrs.pname;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
  };
})
