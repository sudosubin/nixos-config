final: { lib, fetchzip, ... }@prev:

let
  version = "1.3.0";
in
{
  pretendard = fetchzip {
    name = "pretendard-${version}";

    url = "https://github.com/orioncactus/pretendard/releases/download/v${version}/Pretendard-${version}.zip";
    sha256 = "sha256-tjBe2mDZmk0vo4axDlbGOboUPqrA5hQi4tKC4KoZrVo=";

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
