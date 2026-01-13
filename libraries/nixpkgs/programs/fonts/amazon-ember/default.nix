{
  lib,
  stdenvNoCC,
  fetchzip,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "amazon-ember";
  version = "202003";

  src = fetchzip {
    url = "https://m.media-amazon.com/images/G/01/mobile-apps/dex/alexa/branding/Amazon_Typefaces_Complete_Font_Set_Mar2020.zip";
    hash = "sha256-CK7WSXkJkcwMxwdeW31Zs7p2VdZeC3xbpOnmd6Rr9go=";
  };

  installPhase = ''
    runHook preInstall

    install -Dm644 Ember/*.ttf -t $out/share/fonts/truetype

    runHook postInstall
  '';

  meta = {
    description = "Complete set of all Amazon fonts (Bookerly, Amazon Ember)";
    homepage = "https://developer.amazon.com/en-US/alexa/branding/echo-guidelines/identity-guidelines/typography";
    license = {
      fullName = "Amazon Type Library Usage Guidelines";
    };
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.all;
  };
})
