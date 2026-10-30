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
    # Persistent /home volume + EIP re-attach for the Spot + ASG deployment.
    ./spot-home-volume.nix
    ./spot-schedule-guard.nix
    ./spot-protection-observer.nix
    ./spot-work.nix
    ./spot-work-shadow.nix
    ./spot-work-shadow-acp.nix
    ./spot-work-shadow-tui.nix
    ./spot-acp.nix
    ./spot-gateway.nix
    ./spot-profile-cache.nix
  ];

  # Native AWS ASG schedules are independent of this repository or any client.
  # Never arm the on-instance guard before replacement/backup validation.
  services.spotScheduleGuard = {
    enable = true;
    armed = false;
  };

  # Independent read-only status still works with absent/closed work custody.
  # This does not arm or enable termination.
  services.spotProtectionObserver.enable = true;
  # Explicit NEW non-interactive pilot; legacy/provider/output coverage UNKNOWN.
  services.spotWorkShadow.enable = true;
  # Explicit new ACP entry only; never replace an existing TUI/session.
  services.spotWorkShadowAcp.enable = true;
  # Warm opt-in TUI is separate; package the exact public vendor software and
  # verify replacement-root recovery before enabling this declarative package.
  services.spotWorkShadowTui.enable = false;

  services.spotProfileCache.enable = true;

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
    daemon.settings."data-root" = "/home/docker-data";
  };
  systemd.services.docker = {
    requires = [ "home.mount" ];
    after = [ "home.mount" ];
    unitConfig = {
      RequiresMountsFor = "/home/docker-data";
      ConditionPathIsMountPoint = "/home";
    };
  };
  systemd.services."user@1001" = {
    overrideStrategy = "asDropin";
    requires = [ "home.mount" ];
    after = [ "home.mount" ];
    unitConfig.ConditionPathIsMountPoint = "/home";
  };

  # Do not catch up 03:xx maintenance on every scheduled afternoon boot.
  nix.gc.dates = "01:00";
  nix.gc.options = lib.mkForce "--delete-older-than 7d";
  nix.optimise.dates = [ "Sat 01:15" ];
  systemd.timers.nix-gc.timerConfig.Persistent = lib.mkForce false;
  systemd.timers.nix-optimise.timerConfig.Persistent = lib.mkForce false;
  systemd.services.nix-optimise.after = [ "nix-gc.service" ];

  # Compressed RAM swap adds headroom on the 8 GiB Graviton Spot host
  # without provisioning a disk swap file.
  zramSwap.enable = true;

  # Define the primary user account. No password login: access is via SSH
  # keys (over SSM) and passwordless sudo for the wheel group.
  users.users.sudosubin = {
    uid = 1001;
    linger = true;
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
