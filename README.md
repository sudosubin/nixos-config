# Dotfiles

Personal nix files, installs some dotfiles and softwares.

## Installation

```sh
$ nix build .#homeManagerConfigurations.sudosubin.activationPackage
$ ./result/activate
```

## Update lock

```sh
$ nix flake update .
```

## License

Dotfiles is [MIT Licensed](./LICENSE).
