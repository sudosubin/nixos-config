{
  fetchzip,
  lib,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "nanum-square";
  version = "20250212";

  src = fetchzip {
    url = "mirror://ubuntu/pool/universe/f/fonts-nanum/fonts-nanum_${finalAttrs.version}.orig.tar.xz";
    hash = "sha256-yWi8VQhTuZBdppYteJEWgcWSMgk4cqbZcApiB8zn8Iw=";
  };

  installPhase = ''
    runHook preInstall

    install -Dm644 **/NanumFontSetup_OTF_SQUARE/*.otf -t $out/share/fonts/opentype

    runHook postInstall
  '';

  meta = {
    description = "Nanum Square font";
    homepage = "https://hangeul.naver.com/font";
    license = lib.licenses.ofl;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.all;
  };
})
