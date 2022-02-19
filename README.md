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

- SSH Keys `~/.ssh/id_ed25519`, `~/.ssh/id_ed25519.pub`

- Password Store `~/.password-store`

- GitHub CLI `~/.config/gh/hosts.yml`

  ```yml
  github.com:
    user: <USER_NAME>
    oauth_token: <GITHUB_TOKEN>
  ```

- Npm `~/.npmrc`

  ```text
  @<SCOPE>:registry=https://npm.pkg.github.com/
  //npm.pkg.github.com/:_authToken=<NPM_AUTH_TOKEN>
  ```

- Yarn berry `~/.yarnrc.yaml`

  ```yml
  npmScopes:
    <SCOPE>:
      npmRegistryServer: "https://npm.pkg.github.com"
      npmAuthToken: <NPM_AUTH_TOKEN>
  ```

## License

NixOS Config is [MIT Licensed](./LICENSE).
