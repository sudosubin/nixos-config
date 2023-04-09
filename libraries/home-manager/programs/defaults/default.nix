{ config, pkgs, lib, ... }:
with lib;

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.darwin;

  boolValue = x: if x then "YES" else "NO";

  writeValue = value:
    if isBool value then "-bool ${boolValue value}" else
    if isInt value then "-int ${toString value}" else
    if isFloat value then "-float ${strings.floatToString value}" else
    if isString value then "-string '${value}'" else
    throw "invalid value type";

  writeDefault = domain: key: value:
    "defaults write ${domain} '${key}' ${writeValue value}";

  defaultsToList = domain: attrs: mapAttrsToList (writeDefault domain) (filterAttrs (n: v: v != null) attrs);
  defaults = flatten (mapAttrsToList (name: value: defaultsToList name value) cfg.defaults);

in
{
  options.darwin.defaults = mkOption {
    type = types.attrs;
    default = { };
  };

  config = mkMerge [
    (mkIf isDarwin {
      home.activation.userDefaults = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
        ${concatStringsSep "\n" defaults}
      '';
    })
  ];
}
