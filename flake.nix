{
  description = "Nix Configurations";

  inputs = {
    nixpkgs = {
      url = "github:nixos/nixpkgs/nixpkgs-unstable";
    };

    home-manager = {
      url = "github:sudosubin/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, home-manager, ... }: {
    # nixosConfigurations.darwin = nixpkgs.lib.nixosSystem {};

    nixosConfigurations.linux = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        home-manager.nixosModules.home-manager
        ./modules/linux/configuration.nix
        ./modules/linux/home.nix
      ];
    };
  };
}
