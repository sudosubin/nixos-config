{ ... }:

let
  colors = import ../../colors.nix;

  mkColor = foreground: {
    inherit foreground;
    is_bold = false;
    is_underline = false;
    is_dimmed = false;
  };

in
{
  home.shellAliases = {
    l = "eza --all --color=auto --group-directories-first --icons=auto";
    ls = "eza --all --color=auto --color-scale --group --group-directories-first --icons=auto --long --time-style=\"+%Y-%m-%d %H:%M\"";
  };

  programs.eza = {
    enable = true;
    enableBashIntegration = false;

    theme = {
      colourful = true;

      filekinds = {
        normal = mkColor "default";
        directory = mkColor "blue";
        symlink = mkColor "magenta";
        pipe = mkColor "yellow";
        block_device = mkColor "lightred";
        char_device = mkColor "lightred";
        socket = mkColor "green";
        special = mkColor "lightmagenta";
        executable = mkColor "red";
        mount_point = mkColor "lightcyan";
      };

      perms = {
        user_read = mkColor "green";
        user_write = mkColor "yellow";
        user_execute_file = mkColor "red";
        user_execute_other = mkColor "red";
        group_read = mkColor "green";
        group_write = mkColor "yellow";
        group_execute = mkColor "red";
        other_read = mkColor "green";
        other_write = mkColor "yellow";
        other_execute = mkColor "red";
        special_user_file = mkColor "magenta";
        special_other = mkColor "magenta";
        attribute = mkColor "cyan";
      };

      size = {
        major = mkColor colors.foreground;
        minor = mkColor colors.foreground;
        number_byte = mkColor colors.foreground;
        number_kilo = mkColor colors.foreground;
        number_mega = mkColor colors.foreground;
        number_giga = mkColor colors.foreground;
        number_huge = mkColor colors.foreground;
        unit_byte = mkColor colors.foreground;
        unit_kilo = mkColor colors.foreground;
        unit_mega = mkColor colors.foreground;
        unit_giga = mkColor colors.foreground;
        unit_huge = mkColor colors.foreground;
      };

      users = {
        user_you = mkColor "darkgray";
        user_root = mkColor "darkgray";
        user_other = mkColor "darkgray";
        group_yours = mkColor "darkgray";
        group_other = mkColor "darkgray";
        group_root = mkColor "darkgray";
      };

      links = {
        normal = mkColor "blue";
        multi_link_file = mkColor "blue";
      };

      git = {
        new = mkColor "lightgreen";
        modified = mkColor "lightyellow";
        deleted = mkColor "red";
        renamed = mkColor "lightgreen";
        typechange = mkColor "lightyellow";
        ignored = mkColor "darkgray";
        conflicted = mkColor "red";
      };

      git_repo = {
        branch_main = mkColor "lightgray";
        branch_other = mkColor "lightmagenta";
        git_clean = mkColor "lightgreen";
        git_dirty = mkColor "red";
      };

      security_context = {
        none = mkColor "cyan";
        selinux = {
          colon = mkColor "cyan";
          user = mkColor "cyan";
          role = mkColor "cyan";
          typ = mkColor "cyan";
          range = mkColor "cyan";
        };
      };

      file_type = {
        image = mkColor "default";
        video = mkColor "default";
        music = mkColor "default";
        lossless = mkColor "default";
        crypto = mkColor "default";
        document = mkColor "default";
        compressed = mkColor "default";
        temp = mkColor "default";
        compiled = mkColor "default";
        build = mkColor "default";
        source = mkColor "default";
      };

      punctuation = mkColor "darkgray";
      date = mkColor colors.ansi.green;
      inode = mkColor "lightgray";
      blocks = mkColor "darkgray";
      header = mkColor "default";
      octal = mkColor "lightcyan";
      flags = mkColor "lightmagenta";

      symlink_path = mkColor "magenta";
      control_char = mkColor "cyan";
      broken_symlink = mkColor "red";
      broken_path_overlay = mkColor "red";
    };
  };
}
