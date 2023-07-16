{ ... }:

let
  mkConf = conf: { k9s = conf; };

in
{
  programs.k9s = {
    enable = true;

    settings = mkConf {
      refreshRate = 2;
    };

    skin = mkConf {
      fgColor = "dodgerblue";
    };
  };
}
