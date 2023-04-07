{ config, pkgs, ... }:

{
  xdg.dataFile = {
    "com.vercel.cli/config.json".text = builtins.toJSON {
      collectMetrics = false;
    };
  };
}
