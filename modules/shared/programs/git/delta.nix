{ ... }:

let
  colors = import ../../colors.nix // {
    delta.minus-background = "#29171a";
    delta.minus-emph-background = "#5b2223";
    delta.plus-background = "#0d251d";
    delta.plus-emph-background = "#0a4128";
  };

in
{
  programs.delta = {
    enable = true;
    enableGitIntegration = true;
    options = with colors; {
      blame-format = "{timestamp:<14.14} {author:<14.14} {commit:<7.7}";
      blame-palette = "${scale.gray-6} ${scale.gray-7} ${scale.gray-8} ${background}";
      blame-separator-format = "│{n:>4}│";
      blame-separator-style = "black";
      dark = true;
      file-decoration-style = "";
      file-style = "yellow ul";
      grep-context-line-style = "brightblack";
      grep-file-style = "yellow ul";
      grep-line-number-style = "brightblack";
      grep-output-type = "ripgrep";
      hunk-header-decoration-style = "black ul";
      hunk-header-file-style = "brightblack";
      hunk-header-line-number-style = "brightblack";
      inline-hint-style = "brightblack";
      line-numbers-left-style = "black";
      line-numbers-minus-style = "brightblack ${delta.minus-background}";
      line-numbers-plus-style = "brightblack ${delta.plus-background}";
      line-numbers-right-style = "black";
      line-numbers-zero-style = "brightblack";
      minus-emph-style = "syntax ${delta.minus-emph-background}";
      minus-style = "syntax ${delta.minus-background}";
      navigate = true;
      plus-emph-style = "syntax ${delta.plus-emph-background}";
      plus-style = "syntax ${delta.plus-background}";
      relative-paths = true;
      right-arrow = "⟶";
      side-by-side = true;
      syntax-theme = "github-dark";
      tabs = 4;
    };
  };
}
