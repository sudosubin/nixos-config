{ ... }:

let
  colors = import ../../colors.nix // {
    delta.background = "#08000000";
    delta.plus-background = "#003000";
    delta.plus-emph-background = "#004000";
    delta.minus-background = "#400000";
    delta.minus-emph-background = "#500000";
  };

in
{
  programs.delta = {
    enable = true;
    enableGitIntegration = true;
    options = {
      syntax-theme = "base16";
      file-style = "yellow ul";
      file-decoration-style = "";
      hunk-style = "syntax ${colors.delta.background}";
      hunk-header-decoration-style = "${colors.delta.background} ul";
      minus-style = "syntax ${colors.delta.minus-background}";
      minus-emph-style = "syntax ${colors.delta.minus-emph-background}";
      plus-style = "syntax ${colors.delta.plus-background}";
      plus-emph-style = "syntax ${colors.delta.plus-emph-background}";
      whitespace-error-style = "22 reverse";
      side-by-side = true;
      line-numbers-minus-style = "${colors.delta.background} ${colors.delta.minus-background}";
      line-numbers-zero-style = "${colors.delta.background}";
      line-numbers-plus-style = "${colors.delta.background} ${colors.delta.plus-background}";
      line-numbers-left-style = "${colors.delta.background}";
      line-numbers-right-style = "${colors.delta.background}";
    };
  };
}
