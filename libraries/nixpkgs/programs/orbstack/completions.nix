{ pkgs }:
{
  docker = pkgs.docker.src;
  docker-compose = pkgs.fetchFromGitHub {
    owner = "docker";
    repo = "compose";
    rev = "1.29.2";
    sha256 = "sha256-Zx/gVGmYNDWBo/iYr5SDIPTQlzlgLjUx1VMQx5oeV8w=";
  };
}
