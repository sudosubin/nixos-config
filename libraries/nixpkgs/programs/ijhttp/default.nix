final: { lib, stdenvNoCC, fetchurl, unzip, ... }@prev:

{
  ijhttp = stdenvNoCC.mkDerivation rec {
    pname = "ijhttp";
    version = "232.9559.62";

    src = fetchurl {
      url = "https://download-cdn.jetbrains.com/resources/intellij/http-client/${version}/intellij-http-client.zip";
      sha256 = "055j0pls9b5ml8j0csf63wwi001l1a0hbqxds3jdjf86v7d7kg5i";
    };

    nativeBuildInputs = [ unzip ];

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
    '';

    meta = with lib; {
      homepage = "https://blog.jetbrains.com/dotnet/2023/07/04/http-client-tools-everywhere/";
      description = "HTTP Client Tools Everywhere";
      license = licenses.unfree;
      platforms = platforms.unix;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
