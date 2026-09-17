{ config, ... }:

{
  programs.redisinsight = {
    enable = true;
    dataDir = "${config.xdg.dataHome}/redis-insight";
  };
}
