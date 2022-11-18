final: prev:

{
  python310 = prev.python310.override {
    packageOverrides = self: super: {
      # pyopenssl = (import ./pyopenssl self super);
    };
  };
}
