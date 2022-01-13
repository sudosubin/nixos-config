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
    nixosConfigurations.linux = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ./system/linux/configuration.nix
        home-manager.nixosModules.home-manager {
          nixpkgs.config.allowUnfree = true;
          nixpkgs.overlays = [
            (import ./home/overlays/apple-cursor-theme.nix)
            (import ./home/overlays/google-chrome.nix)
            (import ./home/overlays/ll.nix)
            (import ./home/overlays/pipenv.nix)
            (import ./home/overlays/pretendard.nix)
            (import ./home/overlays/vscode.nix)
            (import ./home/overlays/zpl-open.nix)
          ];

          home-manager.useGlobalPkgs = true;
          home-manager.useUserPackages = true;
          home-manager.users.sudosubin = import ./home/linux.nix;
        }
      ];
    };
  };
}
