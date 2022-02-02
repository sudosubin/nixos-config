final: { lib, fetchzip, ... }@prev:

let
  version = "1.2.1";
in
{
  pretendard = fetchzip {
    name = "pretendard-${version}";

    url = "https://github.com/orioncactus/pretendard/releases/download/v${version}/Pretendard-${version}.zip";
    sha256 = "sha256-f/BMerTGc2PW98C+0RK8Sm2hIcWAVMMLNZ2zwi8M8Fs=";

    postFetch = ''
      mkdir -p $out/share/fonts
      unzip -j $downloadedFile "*.otf" -d $out/share/fonts/opentype
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
