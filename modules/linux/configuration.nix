# NixOS system configuration for a headless AWS EC2 (arm64 / Graviton) host.
#
# Access model: AWS Systems Manager (SSM) Session Manager is the primary
# channel, so no inbound ports need to be opened in the security group.
# The OpenSSH daemon is enabled as well (key-only) so that `nixos-rebuild
# --target-host` and interactive SSH can run over an SSM port-forward tunnel.
{
  lib,
  pkgs,
  ...
}:

{
  imports = [
    # EC2 hardware / boot profile (amazon-image).
    ./hardware-configuration.nix
  ];

  # Set your time zone.
  time.timeZone = "Asia/Seoul";

  networking = {
    hostName = "nixos-ec2";
    nameservers = [
      "1.1.1.1"
      "1.0.0.1"
    ];
  };

  # Enable sudo (wheel members may sudo).
  security.sudo.enable = true;

  # Docker
  virtualisation.docker = {
    enable = true;
    autoPrune.enable = true;
  };

  # Compressed RAM swap. This host runs on a small (4 GiB) t4g.medium, so
  # zram provides headroom for memory-heavy Nix builds without provisioning a
  # disk swap file.
  zramSwap.enable = true;

  # Define the primary user account. No password login: access is via SSH
  # keys (over SSM) and passwordless sudo for the wheel group.
  users.users.sudosubin = {
    shell = pkgs.bashInteractive;
    isNormalUser = true;
    extraGroups = [
      "wheel" # Enable ‘sudo’ for the user.
      "docker"
    ];
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAq1R71873LpjHQpJpug71SSovKNnf4V3pvxlaybDueG sudosubin@gmail.com"
    ];
  };

  # Passwordless sudo (no TTY password prompt over SSM/SSH key sessions).
  security.sudo.wheelNeedsPassword = false;

  programs.ssh = {
    startAgent = true;
  };

  programs.nix-ld = {
    enable = true;
  };

  # OpenSSH daemon: key-only, no root/password login. Intended to be reached
  # through an SSM port-forwarding tunnel rather than a public inbound port.
  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = false;
      KbdInteractiveAuthentication = false;
      PermitRootLogin = lib.mkForce "no";
    };
  };

  # AWS Systems Manager agent — enables Session Manager access without any
  # open inbound ports. Requires an IAM instance profile with the
  # `AmazonSSMManagedInstanceCore` managed policy attached.
  services.amazon-ssm-agent.enable = true;

  # Keep the firewall on. SSM needs only outbound 443, so no inbound rules.
  networking.firewall.enable = true;

  environment.pathsToLink = [
    "/libexec"
    "/share/polkit-1"
  ];

  # This value determines the NixOS release from which the default
  # settings for stateful data, like file locations and database versions
  # on your system were taken. Leave at the initial install version.
  system.stateVersion = "22.11";
}
