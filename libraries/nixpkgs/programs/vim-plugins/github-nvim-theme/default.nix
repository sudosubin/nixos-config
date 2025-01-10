{ lib, vimUtils, fetchFromGitHub }:

vimUtils.buildVimPlugin {
  name = "github-nvim-theme";

  src = fetchFromGitHub {
    owner = "projekt0n";
    repo = "github-nvim-theme";
    rev = "v1.1.2";
    sha256 = "0cfdji3c524g7wf7cbr2fpbzrx7my3skgm64d4sgdwa1vgjgmgxs";
  };

  meta = with lib; {
    homepage = "https://github.com/projekt0n/github-nvim-theme";
    description = "GitHub's Neovim themes";
    license = licenses.mit;
    platforms = platforms.all;
    maintainers = [ maintainers.sudosubin ];
  };
}
