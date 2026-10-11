{
  config,
  lib,
  ...
}:

{
  # After setupLaunchAgents (Mic92/sops-nix#911), then sync-install secrets so
  # entryAfter ["sops-nix"] does not race async launchctl bootstrap.
  home.activation = lib.mkIf (config.sops.secrets != { }) {
    sops-nix =
      let
        agent = "org.nix-community.home.sops-nix";
        domain = "gui/$(id -u)";
        plist = "${config.home.homeDirectory}/Library/LaunchAgents/${agent}.plist";
        program = config.launchd.agents.sops-nix.config.Program;

        # Keep sops PATH out of the surrounding activation environment.
        programWithEnv = lib.concatStringsSep " " (
          [ "/usr/bin/env" ]
          ++ map lib.escapeShellArg (
            lib.mapAttrsToList (name: value: "${name}=${toString value}") config.sops.environment ++ [ program ]
          )
        );
      in
      lib.mkForce (
        lib.hm.dag.entryAfter [ "setupLaunchAgents" ] ''
          /bin/launchctl bootout "${domain}/${agent}" || true
          /bin/launchctl bootstrap "${domain}" ${lib.escapeShellArg plist}
          ${programWithEnv}
        ''
      );
  };
}
