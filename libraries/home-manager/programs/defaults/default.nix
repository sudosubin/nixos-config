{
  config,
  pkgs,
  lib,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.darwin;

  boolValue = x: if x then "YES" else "NO";

  writeValue =
    value:
    if lib.isBool value then
      "-bool ${boolValue value}"
    else if lib.isInt value then
      "-int ${toString value}"
    else if lib.isFloat value then
      "-float ${lib.strings.floatToString value}"
    else if lib.isString value then
      "-string '${value}'"
    else
      throw "invalid value type";

  writeDefault =
    domain: key: value:
    "/usr/bin/defaults write ${domain} '${key}' ${writeValue value}";

  defaultsToList =
    domain: attrs: lib.mapAttrsToList (writeDefault domain) (lib.filterAttrs (n: v: v != null) attrs);
  defaults = lib.flatten (lib.mapAttrsToList (name: value: defaultsToList name value) cfg.defaults);

in
{
  options.darwin.defaults = lib.mkOption {
    type = lib.types.attrs;
    default = { };
  };

  config = lib.mkMerge [
    (lib.mkIf isDarwin {
      home.activation.userDefaults = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
        ${lib.concatStringsSep "\n" defaults}
      '';
    })
  ];
}
