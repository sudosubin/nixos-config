{ config, pkgs, lib, ... }:

let
  start-sway = pkgs.writeShellScriptBin "start-sway" ''
    systemctl --user import-environment 2>/dev/null
    exec systemctl --user start sway.service
  '';

in {
  home.packages = with pkgs; [
    start-sway
  ];

  wayland.windowManager.sway = {
    enable = true;
    wrapperFeatures.gtk = true;
  };

  systemd.user.services.sway = {
    Unit = {
      Description = "Sway - Wayland window compositor";
      Documentation = [ "man:sway(5)" ];
      BindsTo = [ "graphical-session.target" ];
      Wants = [ "graphical-session-pre.target" ];
      After = [ "graphical-session-pre.target" ];
    };
    Service = {
      Type = "simple";
      ExecStart = "${pkgs.sway}/bin/sway --debug";
      Restart = "on-failure";
      RestartSec = 1;
      TimeoutSec = 10;
    };
  };
}
