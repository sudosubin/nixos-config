/*
  * https://github.com/NixOS/nixpkgs/commit/ad651f02dd28c56248fdd1fa837c75a04d63113b
*/
final: { ... }@prev:

{
  gdb = prev.gdb.overrideAttrs (attrs: {
    meta.platforms = attrs.meta.platforms ++ [ "aarch64-darwin" ];
  });
}
