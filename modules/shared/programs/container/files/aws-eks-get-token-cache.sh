#!/usr/bin/env bash
set -euo pipefail

die() {
  echo "[ERROR] $*" >&2
  exit 1
}

sanitize() {
  printf '%s' "${1:-default}" | tr -cs '[:alnum:].@_-' '_'
}

CACHE_DIR="${HOME}/.kube/cache"
[[ -n "${KUBECONFIG-}" ]] && CACHE_DIR="$(dirname "${KUBECONFIG%%:*}")/cache"
mkdir -p "$CACHE_DIR"

AWS_ARGS=( "$@" )
CLUSTER_NAME="cluster"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-default}}"
PROFILE="${AWS_PROFILE:-default}"

set -- "${AWS_ARGS[@]}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cluster-name|--cluster-id)
      CLUSTER_NAME="${2:-$CLUSTER_NAME}"
      shift 2
      ;;
    --cluster-name=*|--cluster-id=*)
      CLUSTER_NAME="${1#*=}"
      shift
      ;;
    --region)
      REGION="${2:-$REGION}"
      shift 2
      ;;
    --region=*)
      REGION="${1#*=}"
      shift
      ;;
    --profile)
      PROFILE="${2:-$PROFILE}"
      shift 2
      ;;
    --profile=*)
      PROFILE="${1#*=}"
      shift
      ;;
    --output)
      [[ "${2:-json}" == "json" ]] || die "aws-eks-get-token-cache only supports JSON output."
      shift 2
      ;;
    --output=*)
      [[ "${1#*=}" == "json" ]] || die "aws-eks-get-token-cache only supports JSON output."
      shift
      ;;
    *)
      shift
      ;;
  esac
done

if [[ " ${AWS_ARGS[*]} " != *" eks get-token "* ]]; then
  echo "[ERROR] aws-eks-get-token-cache only supports: eks get-token ..." >&2
  exit 1
fi

if [[ " ${AWS_ARGS[*]} " != *" --output "* && " ${AWS_ARGS[*]} " != *" --output="* ]]; then
  AWS_ARGS+=( --output json )
fi

CACHE_KEY="$(printf '%s\0' "${AWS_PROFILE:-}" "${AWS_REGION:-${AWS_DEFAULT_REGION:-}}" "${AWS_ACCESS_KEY_ID:-}" "${AWS_SESSION_TOKEN:-}" "${AWS_ARGS[@]}" | sha256sum | cut -d' ' -f1)"
CACHE_FILE="${CACHE_DIR}/aws-eks-get-token-$(sanitize "$CLUSTER_NAME")-$(sanitize "$REGION")-$(sanitize "$PROFILE")-${CACHE_KEY}.json"
REFRESH_TIME="$(jq -nr 'now + 30 | todateiso8601')"

if [[ -s "$CACHE_FILE" ]]; then
  EXPIRATION="$(jq -r '.status.expirationTimestamp // empty' "$CACHE_FILE" 2>/dev/null || true)"
  if [[ -n "$EXPIRATION" && "$EXPIRATION" > "$REFRESH_TIME" ]]; then
    cat "$CACHE_FILE"
    exit 0
  fi
fi

TMP_FILE="$(mktemp "${CACHE_FILE}.tmp.XXXXXX")"
trap 'rm -f "$TMP_FILE"' EXIT

aws "${AWS_ARGS[@]}" >"$TMP_FILE"
jq -e '.status.expirationTimestamp and .status.token' "$TMP_FILE" >/dev/null
chmod 600 "$TMP_FILE" 2>/dev/null || true
mv "$TMP_FILE" "$CACHE_FILE"
cat "$CACHE_FILE"
