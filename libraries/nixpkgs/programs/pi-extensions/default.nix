{ callPackage }:

{
  pi-cursor-provider = callPackage ./pi-cursor-provider { };
  pi-cwd-history = callPackage ./pi-cwd-history { };
  pi-interactive-shell = callPackage ./pi-interactive-shell { };
  pi-loop = callPackage ./pi-loop { };
  pi-review = callPackage ./pi-review { };
}
