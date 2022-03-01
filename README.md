<!-- markdownlint-disable MD014 -->

# NixOS Config

Personal nix files, installs some dotfiles and softwares.

## Installation

```sh
# Linux
$ sudo nixos-rebuild --flake '.#linux'

# Darwin
$ nix --experimental-features 'nix-command flakes' build '.#darwinConfigurations.darwin.system'
$ ./result/sw/bin/darwin-rebuild switch --flake '.#darwin'
```

## Update lock

```sh
$ nix flake update .
```

## Additional steps

- SSH keys `~/.ssh/id_ed25519`, `~/.ssh/id_ed25519.pub`

- GPG private keys

- Password Store `~/.password-store`

## License

NixOS Config is [MIT Licensed](./LICENSE).
