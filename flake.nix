{
  description = "Nix home manager flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";

    home-manager.url = "github:nix-community/home-manager";
    home-manager.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, home-manager, ... }: {
    homeManagerConfigurations = {
      sudosubin = home-manager.lib.homeManagerConfiguration { 
        system = "x86_64-linux";
        homeDirectory = "/home/sudosubin";
        username = "sudosubin";
        configuration.imports = [ ./home.nix ];
      };
    };
  };
}
