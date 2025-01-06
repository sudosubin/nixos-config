{ lib, vimUtils, fetchFromGitHub }:

vimUtils.buildVimPlugin {
  name = "github-nvim-theme";

  src = fetchFromGitHub {
    owner = "projekt0n";
    repo = "github-nvim-theme";
    rev = "v1.1.2";
    sha256 = "sha256-ur/65NtB8fY0acTUN/Xw9fT813UiL3YcP4+IwkaUzTE=";
  };

  meta = with lib; {
    homepage = "https://github.com/projekt0n/github-nvim-theme";
    description = "GitHub's Neovim themes";
    license = licenses.mit;
    platforms = platforms.all;
    maintainers = [ maintainers.sudosubin ];
  };
}
