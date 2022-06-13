final: { lib, stdenv, python3, ... }@prev:

let
  py = python3.override {
    packageOverrides = self: super: {
      inherit (import ../python/awscrt self super) awscrt;
      inherit (import ../python/jmespath self super) jmespath;
      inherit (import ../python/pyopenssl self super) pyopenssl;
      inherit (import ../python/twisted self super) twisted;
    };
  };

in
{
  awscli2 =
    if stdenv.isLinux then
      prev.awscli2
    else
      prev.awscli2.override {
        python3 = py // { override = _: py; };
      };
}
