{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    aws-vault
  ];

  home.sessionVariables = {
    AWS_VAULT_BACKEND = "pass";
    AWS_VAULT_PROMPT = "pass";
    AWS_VAULT_PASS_PREFIX = "aws-vault";
    PASS_OATH_CREDENTIAL_NAME = "aws/mathpresso";
  };
}
