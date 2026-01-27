{ ... }:

{
  programs.ssh = {
    enable = true;
    enableDefaultConfig = false;
    matchBlocks."*" = {
      addressFamily = "inet";
      userKnownHostsFile = "~/.ssh/known_hosts";
      extraOptions.StrictHostKeyChecking = "no";
    };
  };
}
