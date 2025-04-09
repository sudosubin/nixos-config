{
  lib,
  buildGoModule,
  fetchFromGitHub,
}:

buildGoModule rec {
  pname = "git-spr";
  version = "0.14.9";

  src = fetchFromGitHub {
    owner = "ejoffe";
    repo = "spr";
    rev = "v${version}";
    sha256 = "sha256-PNKX8XwSmjSevzIYLq13jeHQ1jCuGESKcfwmXVuFM1g=";
  };

  vendorHash = "sha256-nLMEnGqGN62B010NZoG2b0Stg408uz5MbGhiOKRvkIE=";

  postInstall = ''
    mv $out/bin/amend $out/bin/git-amend
    mv $out/bin/reword $out/bin/spr_reword_helper
    mv $out/bin/spr $out/bin/git-spr
  '';

  meta = with lib; {
    description = "Stacked Pull Requests on GitHub";
    homepage = "https://github.com/ejoffe/spr";
    license = licenses.mit;
    platforms = platforms.unix;
    maintainers = with maintainers; [ sudosubin ];
  };
}
