{
  lib,
  stdenvNoCC,
  fetchFromGitHub,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "zpl-open";
  version = "1.1.0";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "zeplin-uri-opener";
    rev = "v${finalAttrs.version}";
    sha256 = "sha256-f6r2vnIGl41C52d1LT6mQpkOXLVLzvkpMivXlwfhMQg=";
  };

  postPatch = ''
    # fix bash invocation
    substituteInPlace src/zpl-open --replace "/bin/bash" "/usr/bin/env bash"

    # fix pkg bin
    substituteInPlace src/zpl-opener.desktop --replace "Exec=zpl-open" "Exec=$out/bin/zpl-open"
  '';

  installPhase = ''
    mkdir -p $out/bin
    mkdir -p $out/share/applications

    cp src/zpl-open $out/bin/
    cp src/zpl-opener.desktop $out/share/applications/
  '';

  meta = {
    description = "Open zeplin app uri in your default browser";
    homepage = "https://github.com/sudosubin/zeplin-uri-opener";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.linux;
    mainProgram = "zpl-open";
  };
})
