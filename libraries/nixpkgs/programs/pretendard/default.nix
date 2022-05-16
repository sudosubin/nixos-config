final: { lib, stdenv, fetchzip, ... }@prev:

let
  version = "1.3.0";

  mkPretendard = { pname, typeface, sha256 }:
    fetchzip {
      name = "${pname}-${version}";

      url = "https://github.com/orioncactus/pretendard/releases/download/v${version}/${typeface}-${version}.zip";
      inherit sha256;

      postFetch = ''
        mkdir -p $out/share/fonts/opentype/${typeface}
        unzip -j $downloadedFile "*.otf" -d $out/share/fonts/opentype/${typeface}/
      '';

      meta = with lib; {
        homepage = "https://github.com/orioncactus/pretendard";
        description = "Pretendard Typeface";
        license = licenses.ofl;
        platforms = platforms.all;
        maintainers = with maintainers; [ sudosubin ];
      };
    };

in
{
  pretendard = mkPretendard {
    pname = "pretendard";
    typeface = "Pretendard";
    sha256 = "sha256-w37Yc4vDbzLJWlP01WhWefQKvx/54sBBMYZZRJ7btg8=";
  };

  pretendard-jp = mkPretendard {
    pname = "pretendard-jp";
    typeface = "PretendardJP";
    sha256 = "sha256-IPchml0KiKiqOxxk0lJDNEwY3omrYfF0SNn2w52abHs=";
  };

  pretendard-std = mkPretendard {
    pname = "pretendard-std";
    typeface = "PretendardStd";
    sha256 = "sha256-cHStOwsMLmGmyPHdyNPjcMnXgrBGBIGoWeavDxY4lSw=";
  };
}
