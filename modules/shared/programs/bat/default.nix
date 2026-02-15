{ ... }:

{
  programs.bat = {
    enable = true;

    config = {
      theme = "github-dark";
      style = "numbers,changes,header";
      italic-text = "always";
    };

    themes = {
      github-dark.src = ./files/github-dark.tmTheme;
    };
  };
}
