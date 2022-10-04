final: { fetchFromGitHub, ... }@prev:

let
  buildSymlinks = prev.runCommand "build-symlinks" { } ''
    mkdir -p $out/bin
    ln -s /usr/bin/xcrun /usr/bin/xcodebuild /usr/bin/tiffutil /usr/bin/qlmanage $out/bin
  '';

in
{
  yabai = prev.yabai.overrideDerivation (attrs: rec {
    pname = "yabai";
    version = "5.0.1";
    name = "${pname}-${version}";

    src = fetchFromGitHub {
      owner = "koekeishiya";
      repo = pname;
      rev = "v${version}";
      sha256 = "sha256-5WtWLfiWVOqshbsx50fuEv8ab3U0y6z5+yvXoxpLokU=";
    };

    nativeBuildInputs = attrs.nativeBuildInputs ++ [ buildSymlinks ];
  });
}
