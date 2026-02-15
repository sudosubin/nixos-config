{ ... }:

{
  programs.jq = {
    enable = true;

    colors = {
      null = "0;34";
      false = "0;34";
      true = "0;34";
      numbers = "0;34";
      strings = "0;94";
      arrays = "0;37";
      objects = "0;37";
      objectKeys = "0;92";
    };
  };
}
