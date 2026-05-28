{ callPackage }:

{
  pi-interactive-shell = callPackage ./pi-interactive-shell { };
  pi-loop = callPackage ./pi-loop { };
  pi-promptsmith = callPackage ./pi-promptsmith { };
  pi-review = callPackage ./pi-review { };
}
