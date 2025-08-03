{
  lib,
  buildGoModule,
  fetchurl,
  unzip,
}:

buildGoModule (finalAttrs: {
  pname = "git-spr";
  version = "0.15.1";

  src = fetchurl {
    url = "https://github.com/ejoffe/spr/archive/refs/tags/v${finalAttrs.version}.zip";
    sha256 = "0sfc4zjw9hazn7kikg42yns92kvkgplz0vzav90c0g0xlzg2l7cq";
  };

  vendorHash = "sha256-vTmzhU/sJ0C8mYuLE8qQQELI4ZwQVv0dsM/ea1mlhFk=";

  nativeBuildInputs = [ unzip ];

  postInstall = ''
    mv $out/bin/amend $out/bin/git-amend
    mv $out/bin/reword $out/bin/spr_reword_helper
    mv $out/bin/spr $out/bin/git-spr
  '';

  meta = with lib; {
    description = "Stacked Pull Requests on GitHub";
    homepage = "https://github.com/ejoffe/spr";
    license = licenses.mit;
    maintainers = with maintainers; [ sudosubin ];
    platforms = platforms.unix;
  };
})
