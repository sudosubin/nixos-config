{
  config,
  lib,
  pkgs,
  ...
}:

{
  programs.lsd = {
    enablePatch = true;

    settings = {
      date = "+%e %b %H:%M";
      size = "bytes";
      sorting.dir-grouping = "first";
      symlink-arrow = "";
    };

    colors = {
      user = "dark_grey";
      group = "dark_grey";
      permission = {
        read = "dark_green";
        write = "dark_yellow";
        exec = "dark_red";
        exec-sticky = "dark_magenta";
        no-access = "dark_grey";
        octal = 6;
        acl = "dark_cyan";
        context = "cyan";
      };
      date = {
        day-old = "white";
        hour-old = "white";
        older = "dark_grey";
      };
      size = {
        none = "dark_grey";
        small = "dark_green";
        medium = "dark_yellow";
        large = "dark_red";
      };
      inode = {
        valid = 13;
        invalid = 245;
      };
      links = {
        valid = 13;
        invalid = 245;
      };
      tree-edge = 245;
      git-status = {
        default = 245;
        unmodified = 245;
        ignored = 245;
        new-in-index = "dark_green";
        new-in-workdir = "dark_green";
        typechange = "dark_yellow";
        deleted = "dark_red";
        renamed = "dark_green";
        modified = "dark_yellow";
        conflicted = "dark_red";
      };
    };

    lscolors = {
      ex = "31"; # ExecutableFile
      fi = "37"; # RegularFile
      di = "34"; # Dir
      ln = "35"; # SymLink
      pi = "33"; # Pipe
      so = "32"; # Socket
      bd = "34;46"; # BlockDevice
      cd = "34;43"; # CharDevice
      or = "31"; # BrokenSymLink
      mi = "31"; # MissingSymLinkTarget
    };
  };
}
