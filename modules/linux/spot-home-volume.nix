# Persistent /home for the Spot + ASG deployment of nixos-ec2.
#
# The instance is replaced (not restarted) on Spot interruption, so /home
# lives on a separate EBS volume tagged `Name=nixos-ec2-home` rather than the
# AMI's root disk. On every boot this module re-discovers that volume by tag
# (it may be attached to a different instance ID each time), attaches it, and
# mounts it by filesystem label so the NVMe device path doesn't matter.
#
# The Elastic IP is re-associated the same way: looked up by
# `Name=nixos-ec2-eip` rather than baked in, since a fresh Spot instance has
# no IP of its own.
{ pkgs, ... }:

let
  awsPath = with pkgs; [
    awscli2
    curl
    jq
  ];
in
{
  environment.systemPackages = with pkgs; [ awscli2 ];

  fileSystems."/home" = {
    device = "/dev/disk/by-label/HOME";
    fsType = "ext4";
    # Don't block boot forever if the volume never shows up — better to boot
    # with an empty /home than to fail to boot at all on a headless box.
    options = [
      "nofail"
      "x-systemd.device-timeout=120"
    ];
  };

  systemd.services.attach-home-volume = {
    description = "Attach the nixos-ec2-home EBS volume before /home is mounted";
    before = [ "home.mount" ];
    requiredBy = [ "home.mount" ];
    after = [ "network-online.target" ];
    wants = [ "network-online.target" ];
    path = awsPath;
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = pkgs.writeShellScript "attach-home-volume" ''
        set -euo pipefail

        TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
        IID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" "http://169.254.169.254/latest/meta-data/instance-id")
        REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" "http://169.254.169.254/latest/meta-data/placement/region")

        VOL_ID=""
        for i in $(seq 1 10); do
          VOL_ID=$(aws ec2 describe-volumes --region "$REGION" \
            --filters "Name=tag:Name,Values=nixos-ec2-home" \
            --query "Volumes[0].VolumeId" --output text 2>/dev/null || true)
          [ -n "$VOL_ID" ] && [ "$VOL_ID" != "None" ] && break
          echo "attach-home-volume: no volume found yet, retrying ($i/10)"
          sleep 5
        done

        if [ -z "$VOL_ID" ] || [ "$VOL_ID" = "None" ]; then
          echo "attach-home-volume: no volume tagged nixos-ec2-home found" >&2
          exit 1
        fi

        for i in $(seq 1 60); do
          INFO=$(aws ec2 describe-volumes --region "$REGION" --volume-ids "$VOL_ID" --output json)
          ATTACHED_TO=$(echo "$INFO" | jq -r '.Volumes[0].Attachments[0].InstanceId // empty')
          ATTACH_STATE=$(echo "$INFO" | jq -r '.Volumes[0].Attachments[0].State // empty')

          if [ "$ATTACHED_TO" = "$IID" ] && [ "$ATTACH_STATE" = "attached" ]; then
            echo "attach-home-volume: already attached to self"
            break
          fi

          if [ -z "$ATTACHED_TO" ]; then
            echo "attach-home-volume: attaching $VOL_ID to $IID"
            aws ec2 attach-volume --region "$REGION" --volume-id "$VOL_ID" --instance-id "$IID" --device /dev/sdf 2>/dev/null || true
          else
            echo "attach-home-volume: still attached to $ATTACHED_TO ($ATTACH_STATE), waiting for detach ($i/60)"
          fi
          sleep 5
        done

        for i in $(seq 1 30); do
          [ -e /dev/disk/by-label/HOME ] && { echo "attach-home-volume: device ready"; exit 0; }
          sleep 2
        done

        echo "attach-home-volume: device did not appear in time" >&2
        exit 1
      '';
    };
  };

  systemd.services.associate-eip = {
    description = "Associate the nixos-ec2 Elastic IP on boot";
    wantedBy = [ "multi-user.target" ];
    after = [ "network-online.target" ];
    wants = [ "network-online.target" ];
    path = awsPath;
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = pkgs.writeShellScript "associate-eip" ''
        set -euo pipefail

        TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
        IID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" "http://169.254.169.254/latest/meta-data/instance-id")
        REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" "http://169.254.169.254/latest/meta-data/placement/region")

        ALLOC_ID=""
        for i in $(seq 1 10); do
          ALLOC_ID=$(aws ec2 describe-addresses --region "$REGION" \
            --filters "Name=tag:Name,Values=nixos-ec2-eip" \
            --query "Addresses[0].AllocationId" --output text 2>/dev/null || true)
          [ -n "$ALLOC_ID" ] && [ "$ALLOC_ID" != "None" ] && break
          echo "associate-eip: no EIP found yet, retrying ($i/10)"
          sleep 5
        done

        if [ -z "$ALLOC_ID" ] || [ "$ALLOC_ID" = "None" ]; then
          echo "associate-eip: no EIP tagged nixos-ec2-eip found" >&2
          exit 1
        fi

        aws ec2 associate-address --region "$REGION" --instance-id "$IID" --allocation-id "$ALLOC_ID" --allow-reassociation
        echo "associate-eip: associated $ALLOC_ID with $IID"
      '';
    };
  };
}
