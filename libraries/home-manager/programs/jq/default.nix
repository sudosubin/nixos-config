{
  config,
  pkgs,
  lib,
  ...
}:

let
  cfg = config.programs.jq-patched;
  c = cfg.colors;

  package = pkgs.jq.overrideAttrs (attrs: {
    nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];

    postFixup = ''
      ${attrs.postFixup or ""}

      wrapProgram $bin/bin/jq \
        --prefix JQ_COLORS "" "${c.null}:${c.false}:${c.true}:${c.numbers}:${c.strings}:${c.arrays}:${c.objects}:${c.fields}";
    '';
  });

in
{
  options.programs.jq-patched = {
    enable = lib.mkEnableOption "jq";

    colors = lib.mkOption {
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

      type = lib.types.submodule {
        options = {
          null = lib.mkOption { type = lib.types.str; };
          false = lib.mkOption { type = lib.types.str; };
          true = lib.mkOption { type = lib.types.str; };
          numbers = lib.mkOption { type = lib.types.str; };
          strings = lib.mkOption { type = lib.types.str; };
          arrays = lib.mkOption { type = lib.types.str; };
          objects = lib.mkOption { type = lib.types.str; };
          fields = lib.mkOption { type = lib.types.str; };
        };
      };
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = [ package ];
  };
}
