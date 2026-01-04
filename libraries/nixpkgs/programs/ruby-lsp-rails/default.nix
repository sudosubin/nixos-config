{
  lib,
  ruby,
  buildRubyGem,
  nix-update-script,
  ruby-lsp,
}:

buildRubyGem rec {
  inherit ruby;
  gemName = "ruby-lsp-rails";
  pname = gemName;
  version = "0.4.8";
  source.sha256 = "sha256-8J0fkm1AY97rLzBJMRklwg3+bJEjceO80EomWoZcRK4=";

  buildInputs = [
    ruby-lsp
  ];

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "A Ruby LSP addon that adds extra editor functionality for Rails applications";
    homepage = "https://github.com/Shopify/ruby-lsp-rails";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
}
