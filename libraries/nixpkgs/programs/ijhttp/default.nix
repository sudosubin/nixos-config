{ lib, stdenvNoCC, fetchurl, unzip, makeWrapper, jdk }:

stdenvNoCC.mkDerivation rec {
  pname = "ijhttp";
  version = "242.21829.56";

  src = fetchurl {
    url = "https://download-cdn.jetbrains.com/resources/intellij/http-client/${version}/intellij-http-client.zip";
    sha256 = "0n99wh3vd023ij2psvb1w7rvjrf69wvdp4w39vrfz904bh4x2a9j";
  };

  nativeBuildInputs = [ unzip makeWrapper ];

  unpackPhase = ''
    unzip $src
  '';

  installPhase = ''
    mkdir -p $out/bin

    cp -r ./ijhttp/* $out
    mv $out/ijhttp $out/bin/ijhttp

    substituteInPlace $out/bin/ijhttp --replace \
      "app_path=\$0" \
      "app_path=\"$out/\""

    wrapProgram $out/bin/ijhttp \
      --prefix JAVA_HOME : "${jdk}"
  '';

  doInstallCheck = true;

  installCheckPhase = ''
    $out/bin/ijhttp --version
  '';

  meta = with lib; {
    homepage = "https://blog.jetbrains.com/dotnet/2023/07/04/http-client-tools-everywhere/";
    description = "HTTP Client Tools Everywhere";
    license = licenses.unfree;
    platforms = platforms.unix;
    maintainers = [ maintainers.sudosubin ];
  };
}
