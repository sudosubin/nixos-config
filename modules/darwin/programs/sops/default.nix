{
  config,
  lib,
  ...
}:

{
  # Unload the RunAtLoad agent and install secrets synchronously, so later steps do not race it.
  home.activation = lib.mkIf (config.sops.secrets != { }) {
    sops-nix =
      let
        agent = "org.nix-community.home.sops-nix";
        domain = "gui/$(id -u)";
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
          /bin/launchctl bootout --wait "${domain}/${agent}" || true
          ${programWithEnv}
        ''
      );
  };
}
