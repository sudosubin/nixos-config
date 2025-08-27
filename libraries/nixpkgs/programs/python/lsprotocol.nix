self: super:

# TODO: fix for pygls
super.lsprotocol.overridePythonAttrs (old: {
  version = "2023.0.1";

  src = self.pkgs.fetchFromGitHub {
    owner = "microsoft";
    repo = "lsprotocol";
    tag = "2023.0.1";
    hash = "sha256-PHjLKazMaT6W4Lve1xNxm6hEwqE3Lr2m5L7Q03fqb68=";
  };
})
