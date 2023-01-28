final: prev:

{
  python310 = prev.python310.override {
    packageOverrides = self: super: { };
  };
}
