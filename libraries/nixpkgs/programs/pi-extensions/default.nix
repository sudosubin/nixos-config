{ callPackage }:

{
  claude-agent-sdk-pi = callPackage ./claude-agent-sdk-pi { };
  pi-cline-free-models = callPackage ./pi-cline-free-models { };
  pi-cursor-agent = callPackage ./pi-cursor-agent { };
  pi-cwd-history = callPackage ./pi-cwd-history { };
  pi-interactive-shell = callPackage ./pi-interactive-shell { };
  pi-review = callPackage ./pi-review { };
}
