self: super: {
  jmespath = super.jmespath.overridePythonAttrs (oldAttrs: rec {
    version = "0.10.0";
    src = self.fetchPypi {
      inherit (oldAttrs) pname;
      inherit version;
      sha256 = "sha256-uF0FZ7hmYUmpMXJxLmiSBzQzPAzn6Jt4s+mH9x5e1Pk=";
    };
  });
}
