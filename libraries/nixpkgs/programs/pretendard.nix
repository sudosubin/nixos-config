final: { lib, fetchzip, ... }@prev:

let
  version = "1.2.1";
in
{
  pretendard = fetchzip {
    name = "pretendard-${version}";

    url = "https://github.com/orioncactus/pretendard/releases/download/v${version}/Pretendard-${version}.zip";
    sha256 = "sha256-tqOKiSwQRx4GYnGK0hlQGk5kUEfXgHv/d4IEG5qleFo=";

    postFetch = ''
      mkdir -p $out/share/fonts/opentype/pretendard
      unzip -j $downloadedFile "*.otf" -d $out/share/fonts/opentype/pretendard/
    '';

    meta = with lib; {
      homepage = "https://github.com/orioncactus/pretendard";
      description = "Pretendard Typeface";
      license = licenses.ofl;
      platforms = platforms.all;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
