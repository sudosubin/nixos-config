{ lib, ... }:

{
  # Keep the upstream input method module without its unsupported GTK2 cache.
  options.home.packages = lib.mkOption {
    apply = lib.filter (pkg: (pkg.name or "") != "gtk2-immodule.cache");
  };

  config.i18n.inputMethod = {
    enable = true;
    type = "kime";
  };
}
