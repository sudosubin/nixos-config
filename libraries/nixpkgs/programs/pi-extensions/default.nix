{ callPackage }:

{
  pi-goal = callPackage ./pi-goal { };
  pi-interactive-shell = callPackage ./pi-interactive-shell { };
  pi-subagent = callPackage ./pi-subagent { };
}
