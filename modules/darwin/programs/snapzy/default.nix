{ ... }:

{
  services.snapzy = {
    enable = true;

    settings = {
      general.export_location = "~/Downloads";
      capture.after.screenshot = {
        save = true;
        quick_access = true;
        copy_file = true;
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
