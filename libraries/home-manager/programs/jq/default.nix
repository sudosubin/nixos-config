{ config, pkgs, lib, ... }:
with lib;

let
  cfg = config.programs.jq-patched;
  c = cfg.colors;

  package = pkgs.jq.overrideAttrs (oldAttrs: {
    patches = (oldAttrs.patches or [ ]) ++ [
      (pkgs.fetchpatch {
        name = "set-field-color-using-jq-colors";
        url = "https://github.com/stedolan/jq/pull/1791.patch";
        sha256 = "sha256-4wCP//PUDNLvps6JklI1a4PFRFeusQDogSNW1E1utU0=";
      })
    ];

    nativeBuildInputs = (oldAttrs.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];

    postInstall = ''
      ${oldAttrs.postInstall or ""}

      wrapProgram $bin/bin/jq \
        --prefix JQ_COLORS "" "${c.null}:${c.false}:${c.true}:${c.numbers}:${c.strings}:${c.arrays}:${c.objects}:${c.fields}";
    '';
  });

in
{
  options.programs.jq-patched = {
    enable = mkEnableOption "jq";

    colors = mkOption {
      description = ''
        The colors used in colored JSON output.</para>
        <para>See <link xlink:href="https://stedolan.github.io/jq/manual/#Colors"/>.
      '';

      default = {
        null = "1;30";
        false = "0;37";
        true = "0;37";
        numbers = "0;37";
        strings = "0;32";
        arrays = "1;37";
        objects = "1;37";
        fields = "1;37";
      };

      type = types.submodule {
        options = {
          null = mkOption { type = types.str; };
          false = mkOption { type = types.str; };
          true = mkOption { type = types.str; };
          numbers = mkOption { type = types.str; };
          strings = mkOption { type = types.str; };
          arrays = mkOption { type = types.str; };
          objects = mkOption { type = types.str; };
          fields = mkOption { type = types.str; };
        };
      };
    };
  };

  config = mkIf cfg.enable {
    home.packages = [ package ];
  };
}
