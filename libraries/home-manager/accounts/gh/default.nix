{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (lib)
    attrValues
    filter
    filterAttrs
    genAttrs
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
  defaultUsernameForHost =
    host:
    let
      primaries = filter (account: account.primary) (attrValues (accountsForHost host));
    in
    if lib.length primaries != 1 then
      throw "accounts.gh: host '${host}' must have exactly one account with primary = true"
    else
      (lib.head primaries).username;

  # Rendered to YAML via pkgs.formats.yaml instead of hand-built strings.
  hostsData = genAttrs hosts (host: {
    users = mapAttrs' (
      name: account:
      nameValuePair account.username {
        oauth_token = config.sops.placeholder."gh-token-${name}";
        git_protocol = "https";
      }
    ) (accountsForHost host);
    user = defaultUsernameForHost host;
    git_protocol = "https";
  });

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
      nameValuePair "gh-token-${name}" {
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
