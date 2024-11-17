<!-- markdownlint-disable MD014 -->

# NixOS Config

Personal nix files, installs some dotfiles and softwares.

## Installation

```sh
# Linux
$ nixos-rebuild switch --flake '.#linux' --use-remote-sudo

# Darwin
$ nix --experimental-features 'nix-command flakes' build '.#darwinConfigurations.darwin.system'
$ ./result/sw/bin/darwin-rebuild switch --flake '.#darwin'
```

## Update (flake lock, custom packages)

```sh
$ nix flake update --flake .
fetching ...

$ ./scripts/auto-update-modules.py
fetching ...
```

## Additional steps

- SSH keys `~/.ssh/id_ed25519`, `~/.ssh/id_ed25519.pub`

- GPG private keys

## License

NixOS Config is [MIT Licensed](./LICENSE).
