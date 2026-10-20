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
      keep-outputs = true
      keep-derivations = true
      experimental-features = nix-command flakes
    '';
  };
}
