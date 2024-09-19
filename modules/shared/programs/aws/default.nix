{ config, pkgs, ... }:

{
  home.sessionVariables = {
    AWS_VAULT_BACKEND = "file";
    AWS_VAULT_FILE_DIR = "~/.config/aws-vault/keys";
    AWS_VAULT_FILE_PASSPHRASE = "";
  };

  home.packages = with pkgs; [
    awscli2
    aws-vault
    ssm-session-manager-plugin
  ];
}
