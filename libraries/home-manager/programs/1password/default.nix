{
  config,
  pkgs,
  lib,
  ...
}:

let
  cfg = config.programs._1password;

  makeWrapperFHSEnvironment = pkgs.runCommand "wrap-fhs-environment.sh" { } ''
    substitute ${./wrap-fhs-environment.sh} $out \
      --replace @shell@ ${pkgs.bash}/bin/bash \
      --replace @sha256sum@ ${pkgs.coreutils}/bin/sha256sum
  '';

  package =
    if cfg.enableFHSEnvironment then
      cfg.package.overrideAttrs (attrs: {
        nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];

        postInstall = ''
          ${attrs.postInstall or ""}
          source ${makeWrapperFHSEnvironment}
          wrapFHSEnvironment "$out/bin/op" "/usr/local/bin/op"
        '';

        doInstallCheck = false;
      })
    else
      cfg.package;

in
{
  options.programs._1password = {
    enable = lib.mkEnableOption "1password";

    package = lib.mkPackageOption pkgs "_1password" { };

    enableFHSEnvironment = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Enable /usr/local/bin/op binary to connect with 1Password app.";
    };
  };

  config = lib.mkMerge [
    (lib.mkIf cfg.enable {
      home.packages = [ package ];
    })
  ];
}
