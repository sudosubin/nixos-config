{ config, pkgs, ... }:

{
  home.sessionVariables = {
    AWS_VAULT_BACKEND = "file";
    AWS_VAULT_PROMPT = "1password";
    AWS_VAULT_FILE_PASSPHRASE = "";
  };

  home.packages = with pkgs; [
    awscli2
    aws-vault
  ];
}
