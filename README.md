# Dotfiles

Personal nix files, installs some dotfiles and softwares.

## Installation

- You need `~/.ssh/id_ed25519`, `~/.config/sops/age/keys.txt` files

```sh
# TODO: Add darwin variant
$ sudo nixos-rebuild --flake '.#linux'
```

## Update lock

```sh
$ nix flake update .
```

## License

Dotfiles is [MIT Licensed](./LICENSE).
