final: prev:

{
  lib = prev.lib.extend (self: super: {
    generators = prev.lib.generators // {
      toXML = (import ./xml.nix { lib = prev.lib; });
    };
  });
}
