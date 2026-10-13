{ ... }:

{
  services.snapzy = {
    enable = true;

    settings = {
      general.export_location = "~/Downloads";
      capture.after.screenshot = {
        save = true;
        quick_access = true;
        copy_file = false;
      };
      quick_access = {
        position = "bottomLeft";
        auto_dismiss = false;
      };
      recording = {
        remember_last_area = true;
        show_cursor = false;
        show_keystrokes = true;
      };
      shortcuts.enabled = false;
    };

    config = {
      onboardingCompleted = true;
      splashSkipped = true;
      sponsorPromptSeen = true;
    };
  };
}
