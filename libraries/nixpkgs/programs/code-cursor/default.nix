final: prev:

let
  inherit (prev.stdenvNoCC.hostPlatform) isDarwin isLinux;

in
{
  code-cursor = prev.code-cursor.overrideAttrs (attrs: {
    dontUpdateAutotoolsGnuConfigScripts = isDarwin;
  });
}
