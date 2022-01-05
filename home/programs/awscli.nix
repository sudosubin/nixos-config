{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    aws-vault
    awscli2
  ];

  home.sessionVariables = {
    AWS_VAULT_BACKEND = "pass";
    AWS_VAULT_PROMPT = "pass";
    AWS_VAULT_PASS_PREFIX = "aws-vault";
    PASS_OATH_CREDENTIAL_NAME = "aws/mathpresso";
  };

  home.file = {
    ".aws/config".text = ''
      [default]
      region = ap-northeast-2
    '';
  };
}
