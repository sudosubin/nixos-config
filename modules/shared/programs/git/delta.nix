{ config, pkgs, ... }:

{
  programs.git.delta = {
    enable = true;
    options = {
      syntax-theme = "GitHub";
      light = true;
      file-style = "yellow ul";
      file-decoration-style = "";
      hunk-style = "syntax #6e7781";
      hunk-header-decoration-style = "#6e7781 ul";
      minus-style = "syntax #FFEBE9";
      minus-emph-style = "syntax #FFC1BF";
      plus-style = "syntax #E6FFEC";
      plus-emph-style = "syntax #ABF2BC";
      whitespace-error-style = "#ABF2BC #ABF2BC";
      side-by-side = true;
      line-numbers-minus-style = "#6e7781 #FFEBE9";
      line-numbers-zero-style = "#6e7781";
      line-numbers-plus-style = "#6e7781 #E6FFEC";
      line-numbers-left-style = "#6e7781";
      line-numbers-right-style = "#6e7781";
    };
  };
}
