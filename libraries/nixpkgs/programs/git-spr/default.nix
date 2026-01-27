{
  buildGoModule,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildGoModule (finalAttrs: {
  pname = "git-spr";
  version = "0.16.0";

  src = fetchFromGitHub {
    owner = "ejoffe";
    repo = "spr";
    rev = "v${finalAttrs.version}";
    hash = "sha256-caEBsxajmjV7yr86WskkRBYBFzdV29wqu44fwMDowGw=";
  };

  vendorHash = "sha256-byl+MF0vlfa4V/3uPrv5Qlcvh5jIozEyUkKSSwlRWhs=";

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
