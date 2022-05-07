{ config, lib, pkgs, ... }:

let
  theme-name = "custom";

in
{
  programs.lsd = {
    enablePatch = true;

    settings = {
      color.theme = theme-name;
      date = "+%e %b %H:%M";
      size = "bytes";
      sorting.dir-grouping = "first";
      symlink-arrow = "";
    };

    colors = {
      di = "34"; # Directory
      ex = "31"; # Executable file
      pi = "33"; # Named pipe
      so = "32"; # Socket
      bd = "34;46"; # Block device
      cd = "34;43"; # Character device
      ln = "35"; # Symlink
      or = "31"; # Broken symlink
    } // (import ./lscolors.nix);

    themes."${theme-name}" = {
      user = "dark_grey";
      group = "dark_grey";
      permission = {
        read = "dark_green";
        write = "dark_yellow";
        exec = "dark_red";
        exec-sticky = "dark_magenta";
        no-access = "dark_grey";
      };
      date = {
        hour-old = "white";
        day-old = "white";
        older = "dark_grey";
      };
      size = {
        none = "dark_grey";
        small = "dark_green";
        medium = "dark_yellow";
        large = "dark_red";
      };
    };
  };
}
