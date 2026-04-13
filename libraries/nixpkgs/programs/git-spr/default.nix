{
  buildGoModule,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildGoModule (finalAttrs: {
  pname = "git-spr";
  version = "0.17.4";

  src = fetchFromGitHub {
    owner = "ejoffe";
    repo = "spr";
    rev = "v${finalAttrs.version}";
    hash = "sha256-xgA/C8kl404TiRZuJsH10bu4TZuzWOgdix1ESb9KY9M=";
  };

  vendorHash = "sha256-VB7OJ8UkZ0WhEM5l2wR3xA1yxZcr+G+FLt3MxNY83Tg=";

  postInstall = ''
    mv $out/bin/amend $out/bin/git-amend
    mv $out/bin/reword $out/bin/spr_reword_helper
    mv $out/bin/spr $out/bin/git-spr
  '';

  passthru.updateScript = nix-update-script { };

  meta = with lib; {
    description = "Stacked Pull Requests on GitHub";
    homepage = "https://github.com/ejoffe/spr";
    license = licenses.mit;
    maintainers = with maintainers; [ sudosubin ];
    platforms = platforms.unix;
  };
})
