{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (lib)
    attrNames
    attrValues
    filterAttrs
    genAttrs
    head
    length
    mapAttrs'
    mapAttrsToList
    nameValuePair
    unique
    ;

  yamlFormat = pkgs.formats.yaml { };

  cfg = config.accounts.gh;

  hosts = unique (mapAttrsToList (_name: account: account.host) cfg);

  accountsForHost = host: filterAttrs (_name: account: account.host == host) cfg;

  # gh's hosts.yml allows exactly one active `user` per host.
  primaryForHost =
    host:
    let
      primaries = filterAttrs (_name: account: account.primary) (accountsForHost host);
    in
    if length (attrNames primaries) != 1 then
      throw "accounts.gh: host '${host}' must have exactly one account with primary = true"
    else
      nameValuePair (head (attrNames primaries)) (head (attrValues primaries));

  mkTokenName = name: "gh-token-${name}";

  # Rendered to YAML via pkgs.formats.yaml instead of hand-built strings.
  hostsData = genAttrs hosts (
    host:
    let
      primary = primaryForHost host;
    in
    {
      users = mapAttrs' (
        name: account:
        nameValuePair account.username {
          oauth_token = config.sops.placeholder.${mkTokenName name};
          git_protocol = "https";
        }
      ) (accountsForHost host);

      # gh reads the active account's token from the host level, not from `users`.
      user = primary.value.username;
      oauth_token = config.sops.placeholder.${mkTokenName primary.name};
      git_protocol = "https";
    }
  );

in
{
  options.accounts.gh = lib.mkOption {
    default = { };
    description = "GitHub accounts to register in gh's `hosts.yml`.";
    type = lib.types.attrsOf (
      lib.types.submodule {
        options = {
          host = lib.mkOption {
            type = lib.types.str;
            default = "github.com";
            description = "GitHub hostname this account belongs to.";
          };

          username = lib.mkOption {
            type = lib.types.str;
            description = "Account username on this host.";
          };

          file = lib.mkOption {
            type = lib.types.path;
            description = "sops-encrypted file (binary format) containing the oauth token.";
          };

          primary = lib.mkOption {
            type = lib.types.bool;
            default = true;
            description = "Whether this account is the active (`user`) account for its host.";
          };
        };
      }
    );
  };

  config = lib.mkIf (cfg != { }) {
    sops.secrets = mapAttrs' (
      name: account:
      nameValuePair (mkTokenName name) {
        sopsFile = account.file;
        format = "binary";
      }
    ) cfg;

    sops.templates."gh-hosts.yml".file = yamlFormat.generate "gh-hosts.yml" hostsData;

    xdg.configFile."gh/hosts.yml".source =
      config.lib.file.mkOutOfStoreSymlink
        config.sops.templates."gh-hosts.yml".path;
  };
}
