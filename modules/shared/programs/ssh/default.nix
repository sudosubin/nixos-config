{ ... }:

{
  programs.ssh = {
    enable = true;
    enableDefaultConfig = false;
    settings."*" = {
      AddressFamily = "inet";
      UserKnownHostsFile = "~/.ssh/known_hosts";
      StrictHostKeyChecking = "no";
    };
  };
}
