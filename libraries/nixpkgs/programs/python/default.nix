final: prev:

{
  python313 = prev.python313.override {
    packageOverrides = self: super: {
      lsprotocol = (import ./lsprotocol.nix self super);
    };
  };
}
