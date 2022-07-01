self: super: {
  awscrt = super.awscrt.overridePythonAttrs (attrs: rec {
    version = "0.13.5";
    src = self.fetchPypi {
      inherit (attrs) pname;
      inherit version;
      sha256 = "sha256-dUNljMKsbl6eByhEYivWgRJczTBw3N1RVl8r3e898mg=";
    };
  });
}
