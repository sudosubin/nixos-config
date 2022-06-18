final: { lib, stdenv, ... }@prev:

{
  aws-vault = prev.aws-vault.overrideDerivation (attrs: rec {
    postPatch = ''
      cp ${./prompt-1password.go} ./prompt/1password.go
    '';
  });
}
