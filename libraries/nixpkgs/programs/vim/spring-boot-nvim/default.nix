{
  vimUtils,
  fetchFromGitHub,
}:

vimUtils.buildVimPlugin {
  pname = "spring-boot-nvim";
  version = "0-unstable-2024-06-07";

  src = fetchFromGitHub {
    owner = "JavaHello";
    repo = "spring-boot.nvim";
    rev = "218c0c2";
    hash = "sha256-5mzAr+VS5RGLi5e+ZohrlVHUzPa+6JwEWi4cslKPMNA=";
  };

  nvimSkipModules = [
    "spring_boot.config"
    "spring_boot.jdtls"
    "spring_boot.java_data"
    "spring_boot.launch"
  ];

  meta.homepage = "https://github.com/JavaHello/spring-boot.nvim/";
  meta.hydraPlatforms = [ ];
}
