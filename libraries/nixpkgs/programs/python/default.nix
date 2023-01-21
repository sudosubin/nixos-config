final: prev:

{
  python310 = prev.python310.override {
    packageOverrides = self: super: {
      jedi-language-server = (import ./jedi-language-server self super);
      lsprotocol = (import ./lsprotocol self super);
      pygls = (import ./pygls self super);
    };
  };
}
