# EC2 (arm64 / Graviton) hardware profile.
#
# The upstream `amazon-image` NixOS profile wires up everything the Nitro
# platform needs: the ENA network driver, NVMe/EBS root device, GRUB (with
# UEFI on aarch64), partition auto-growth and the EC2 metadata/init handling.
# We therefore import it instead of a `nixos-generate-config` hardware scan.
{
  lib,
  modulesPath,
  ...
}:

{
  imports = [
    "${modulesPath}/virtualisation/amazon-image.nix"
  ];

  # Graviton instances are 64-bit ARM.
  nixpkgs.hostPlatform = lib.mkDefault "aarch64-linux";

  # Grow the root partition to fill the whole EBS volume on first boot.
  boot.growPartition = lib.mkDefault true;
}
