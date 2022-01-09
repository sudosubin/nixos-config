{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    noto-fonts
    noto-fonts-cjk
    noto-fonts-emoji
    pretendard
    (nerdfonts.override { fonts = [ "FiraMono" ]; })
  ];

  fonts.fontconfig = {
    enable = true;
  };

  xdg.configFile = {
    "fontconfig/fonts.conf".text = ''
      <?xml version="1.0"?>
      <!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
      <fontconfig>
        <!-- serif -->
        <alias>
          <family>serif</family>
          <prefer><family>Noto Serif CJK KR</family></prefer>
        </alias>
        <!-- sans serif -->
        <alias>
          <family>sans-serif</family>
          <prefer><family>Pretendard</family></prefer>
          <prefer><family>Noto Sans CJK KR</family></prefer>
          <prefer><family>Noto Sans CJK JP</family></prefer>
          <prefer><family>Noto Sans CJK TC</family></prefer>
          <prefer><family>Noto Sans CJK SC</family></prefer>
         <prefer><family>Noto Sans CJK HK</family></prefer>
       </alias>
       <!-- sans -->
       <alias>
          <family>sans</family>
          <prefer><family>Pretendard</family></prefer>
          <prefer><family>Noto Sans CJK KR</family></prefer>
          <prefer><family>Noto Sans CJK JP</family></prefer>
          <prefer><family>Noto Sans CJK TC</family></prefer>
          <prefer><family>Noto Sans CJK SC</family></prefer>
          <prefer><family>Noto Sans CJK HK</family></prefer>
        </alias>
        <!-- sans serif -->
        <alias>
          <family>-apple-system</family>
          <prefer><family>Pretendard</family></prefer>
          <prefer><family>Noto Sans CJK KR</family></prefer>
          <prefer><family>Noto Sans CJK JP</family></prefer>
          <prefer><family>Noto Sans CJK TC</family></prefer>
          <prefer><family>Noto Sans CJK SC</family></prefer>
          <prefer><family>Noto Sans CJK HK</family></prefer>
        </alias>
        <!-- monospace -->
        <alias>
          <family>monospace</family>
          <prefer><family>FiraMono Nerd Font Mono</family></prefer>
        </alias>
      </fontconfig>
    '';
  };
}
