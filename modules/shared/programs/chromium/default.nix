{
  config,
  pkgs,
  lib,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;

in
{
  programs.chromium = {
    enable = true;
    package' = pkgs.ungoogled-chromium;

    extensions' = [
      pkgs.chrome-web-store._1password
      pkgs.chrome-web-store.claude
      pkgs.chrome-web-store.neutral-face-emoji-tools
      pkgs.chrome-web-store.react-developer-tools
      pkgs.chrome-web-store.trancy
      pkgs.chrome-web-store.ublock-origin-lite
    ];

    defaultOpts = lib.mkIf isDarwin {
      AutofillAddressEnabled = false;
      AutofillCreditCardEnabled = false;
      DefaultBrowserSettingEnabled = false;
      DefaultNotificationsSetting = 2;
      DefaultSearchProviderEnabled = true;
      DefaultSearchProviderSearchURL = "https://google.com/search?q={searchTerms}";
      DefaultSearchProviderSuggestURL = "https://google.com/complete/search?output=chrome&q={searchTerms}";
      DeveloperToolsAvailability = 1;
      ManagedBookmarks = [
        {
          name = "Notepad";
          url = "data:text/html, <body contenteditable style=\"font:30px monospace;max-width:60rem;margin:0 auto;padding:4rem;color:white;background:%233c3c3c\" autofocus>";
        }
      ];
      PasswordManagerEnabled = false;
      WebRtcIPHandling = "disable_non_proxied_udp";
    };

    initialPrefs = lib.mkIf isDarwin {
      bookmark_bar = {
        show_on_all_tabs = false;
        show_tab_groups = false;
      };
      browser.enable_spellchecking = false;
      distribution.browser.confirm_to_quit = true;
      webkit = {
        webprefs.fonts.fixed.Zyyy = "PragmataProMono Nerd Font Mono";
        webprefs.fonts.sansserif.Zyyy = "Pretendard";
        webprefs.fonts.serif.Zyyy = "Noto Serif";
        webprefs.fonts.standard.Zyyy = "Pretendard";
      };
    };
  };
}
