{
  lib,
  stdenvNoCC,
  fetchurl,
  unzip,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "s-core-dream";
  version = "202003";

  src = fetchurl {
    url = "https://s-core.co.kr/wp-content/uploads/2020/03/S-Core_Dream_OTF.zip";
    hash = "sha256-qy0Y8PFC5Gug9MfCiQ6k8uYE2FJWeBwolTE2IF4dDl4=";
  };

  nativeBuildInputs = [ unzip ];

  # ignores illegal byte sequence
  unpackPhase = ''
    runHook preUnpack

    unzip -j $src '*.otf' || true

    runHook postUnpack
  '';

  installPhase = ''
    runHook preInstall

    install -Dm644 *.otf -t $out/share/fonts/opentype

    runHook postInstall
  '';

  meta = {
    description = "S-Core Dream font";
    homepage = "https://s-core.co.kr/company/font2/";
    license = {
      fullName = "Amazon Type Library Usage Guidelines";
      url = "https://s-core.co.kr/company/font2/";
    };
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.all;
  };
})
