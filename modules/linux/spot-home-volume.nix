# One explicit EBS identity: never select Volumes[0] from an ambiguous tag query.
# Missing/wrong home blocks workloads, not the independent SSM recovery agent.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  guard = config.services.spotScheduleGuard;
  awsPath = with pkgs; [
    awscli2
    curl
    jq
    coreutils
    util-linux
  ];
  profileGate = lib.optional config.services.spotProfileCache.enable "spot-profile-cache-restore.service";
  metadata = ''
    set -euo pipefail
    unset AWS_PROFILE AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
    export AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_PAGER=""
    TOKEN=$(curl --fail --silent --show-error --max-time 3 -X PUT \
      http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 21600')
    IID=$(curl --fail --silent --show-error --max-time 3 -H "X-aws-ec2-metadata-token: $TOKEN" \
      http://169.254.169.254/latest/meta-data/instance-id)
    REGION=$(curl --fail --silent --show-error --max-time 3 -H "X-aws-ec2-metadata-token: $TOKEN" \
      http://169.254.169.254/latest/meta-data/placement/region)
    [ "$REGION" = ${lib.escapeShellArg guard.region} ]
  '';
in
{
  environment.systemPackages = [ pkgs.awscli2 ];
  fileSystems."/home" = {
    device = "/dev/disk/by-uuid/${guard.homeUUID}";
    fsType = "ext4";
    options = [
      "nofail"
      "x-systemd.device-timeout=120"
    ];
  };
  systemd.services.attach-home-volume = {
    description = "Attach and verify the explicit persistent home EBS identity";
    before = [ "home.mount" ];
    requiredBy = [ "home.mount" ];
    requires = [ "spot-scale-in-protection-ready.service" ];
    after = [
      "network-online.target"
      "spot-scale-in-protection-ready.service"
    ];
    wants = [ "network-online.target" ];
    path = awsPath;
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      TimeoutStartSec = 420;
      ExecStart = pkgs.writeShellScript "attach-home-volume" ''
        ${metadata}
        # Only root can override this path (e.g. a scoped clone-validation config).
        STORAGE_CONFIG="''${SPOT_STORAGE_CONFIG:-/etc/spot-schedule-guard.json}"
        VOL_ID=$(jq -er '.home_volume' "$STORAGE_CONFIG")
        EXPECTED_UUID=$(jq -er '.home_uuid' "$STORAGE_CONFIG")
        [[ "$VOL_ID" =~ ^vol-[0-9a-f]+$ ]] || exit 1
        [[ "$EXPECTED_UUID" =~ ^[0-9a-f-]{36}$ ]] || exit 1
        ATTACHED=false
        for i in $(seq 1 60); do
          INFO=$(aws ec2 describe-volumes --region "$REGION" --volume-ids "$VOL_ID" --output json)
          [ "$(printf '%s' "$INFO" | jq '.Volumes | length')" = 1 ]
          ATTACHED_TO=$(printf '%s' "$INFO" | jq -r '.Volumes[0].Attachments[0].InstanceId // empty')
          ATTACH_STATE=$(printf '%s' "$INFO" | jq -r '.Volumes[0].Attachments[0].State // empty')
          if [ "$ATTACHED_TO" = "$IID" ] && [ "$ATTACH_STATE" = attached ]; then
            ATTACHED=true
            break
          fi
          if [ -z "$ATTACHED_TO" ]; then
            aws ec2 attach-volume --region "$REGION" --volume-id "$VOL_ID" --instance-id "$IID" --device /dev/sdf >/dev/null || true
          fi
          # Never force-detach a volume still owned by the previous instance.
          sleep 5
        done
        [ "$ATTACHED" = true ] || { echo 'Home volume attachment is not verified' >&2; exit 1; }
        SERIAL=$(printf '%s' "$VOL_ID" | tr -d '-')
        for i in $(seq 1 30); do
          for serial in /sys/class/block/nvme*n1/device/serial; do
            [ -r "$serial" ] || continue
            [ "$(tr -d '[:space:]' < "$serial")" = "$SERIAL" ] || continue
            device=/dev/$(basename "$(dirname "$(dirname "$serial")")")
            [ "$(blkid -c /dev/null -s UUID -o value "$device")" = "$EXPECTED_UUID" ] || exit 1
            [ -e "/dev/disk/by-uuid/$EXPECTED_UUID" ] || continue
            [ "$(readlink -f "/dev/disk/by-uuid/$EXPECTED_UUID")" = "$device" ] || exit 1
            echo 'Persistent home EBS serial and filesystem UUID verified'
            exit 0
          done
          sleep 2
        done
        echo 'Expected home device did not appear; refusing a fallback home' >&2
        exit 1
      '';
    };
  };
  systemd.services.associate-eip = {
    description = "Associate production EIP only after persistent data is ready";
    wantedBy = [ "multi-user.target" ];
    requires = [ "home.mount" ] ++ profileGate;
    after = [
      "network-online.target"
      "home.mount"
    ]
    ++ profileGate;
    wants = [ "network-online.target" ];
    path = awsPath;
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = pkgs.writeShellScript "associate-eip" ''
        ${metadata}
        [ "$(findmnt -n -o TARGET --target /home)" = /home ]
        [ "$(findmnt -n -o UUID --target /home)" = ${lib.escapeShellArg guard.homeUUID} ]
        aws ec2 associate-address --region "$REGION" --instance-id "$IID" \
          --allocation-id eipalloc-04d6e702ea3b20bd7 --allow-reassociation >/dev/null
      '';
    };
  };
}
