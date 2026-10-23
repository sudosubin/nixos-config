{ callPackage }:

{
  pi-goal = callPackage ./pi-goal { };
  pi-interactive-shell = callPackage ./pi-interactive-shell { };
  pi-review = callPackage ./pi-review { };
  pi-subagent = callPackage ./pi-subagent { };
}
