{
  coreutils,
  fetchFromGitHub,
  installShellFiles,
  lib,
  nix-update-script,
  runtimeShell,
  rustPlatform,
  stdenv,
  util-linux,
  versionCheckHook,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "linear-cli";
  version = "3.1.0";

  src = fetchFromGitHub {
    owner = "schpet";
    repo = "linear-cli";
    tag = "v${finalAttrs.version}";
    hash = "sha256-Bk4UPFqKVFH51iqiEhCSVfy/CX8CBnD8pHMMCIT83Pw=";
  };

  cargoHash = "sha256-FTm/RheZVjqILLM+T9JF5agZQOZF2OILI8znfZvw4Ms=";

  nativeBuildInputs = [ installShellFiles ];

  # The upstream test helpers use system paths that are absent in the Nix sandbox.
  postPatch = lib.optionalString stdenv.hostPlatform.isLinux ''
    substituteInPlace \
      crates/linear-cli/src/auth/keyring/process/tests.rs \
      crates/linear-cli/src/platform/editor.rs \
      crates/linear-cli/tests/cli/issue_read.rs \
      crates/linear-cli/tests/cli/support/sandbox.rs \
      --replace-fail /bin/sh ${runtimeShell}

    substituteInPlace crates/linear-cli/src/auth/file.rs \
      --replace-fail /usr/bin/mkfifo ${lib.getExe' coreutils "mkfifo"}
    substituteInPlace crates/linear-cli/src/auth/keyring/process/tests.rs \
      --replace-fail /bin/cat ${lib.getExe' coreutils "cat"} \
      --replace-fail /bin/sleep ${lib.getExe' coreutils "sleep"} \
      --replace-fail /bin/kill ${lib.getExe' coreutils "kill"}
    substituteInPlace crates/linear-cli/tests/cli/support/sandbox.rs \
      --replace-fail /usr/bin/script ${lib.getExe' util-linux "script"} \
      --replace-fail PATH=/usr/bin:/bin PATH=${lib.makeBinPath [ coreutils ]}
  '';

  postInstall = ''
    installShellCompletion --cmd linear \
      --bash <($out/bin/linear completions bash) \
      --fish <($out/bin/linear completions fish) \
      --zsh <($out/bin/linear completions zsh)
  '';

  doInstallCheck = true;
  nativeInstallCheckInputs = [ versionCheckHook ];
  versionCheckProgram = "${placeholder "out"}/bin/linear";

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "CLI tool for linear.app that uses git branch names and directory names to open issues and team pages";
    homepage = "https://github.com/schpet/linear-cli";
    license = lib.licenses.isc;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "linear";
    platforms = [
      "aarch64-darwin"
      "aarch64-linux"
      "x86_64-linux"
    ];
  };
})
