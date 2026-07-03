{ callPackage }:

{
  pi-goal = callPackage ./pi-goal { };
  pi-interactive-shell = callPackage ./pi-interactive-shell { };
  pi-promptsmith = callPackage ./pi-promptsmith { };
  pi-review = callPackage ./pi-review { };
}
