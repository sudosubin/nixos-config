{ ... }:

{
  nix = {
    gc = {
      automatic = true;
      options = "--delete-old";
    };
    optimise = {
      automatic = true;
    };
    settings = {
      use-xdg-base-directories = true;
    };
    extraOptions = ''
      experimental-features = nix-command flakes
    '';
  };
}
