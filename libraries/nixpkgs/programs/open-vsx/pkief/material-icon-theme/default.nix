{
  jq,
  material-icon-theme,
  nodejs,
  open-vsx,
  settings ? { },
}:

open-vsx.pkief.material-icon-theme.overrideAttrs (attrs: {
  nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [
    jq
    nodejs
  ];

  # the extension version is pinned by the nix-vscode-extensions input, not by this file
  passthru = removeAttrs (attrs.passthru or { }) [ "updateScript" ];

  preInstall = ''
    ${attrs.preInstall or ""}

    # the extension applies settings by rewriting its manifest, which fails in the read-only store
    node -p 'JSON.stringify(require(process.argv[1]).generateManifest(require(process.argv[2])))' \
      ${material-icon-theme}/lib/node_modules/material-icon-theme/dist/module/index.cjs \
      ${builtins.toFile "settings.json" (builtins.toJSON settings)} \
      > ./dist/material-icons.json

    # take the icons from the same release as the manifest so the two never drift apart
    rm -r ./icons
    cp -r --no-preserve=mode ${material-icon-theme}/lib/node_modules/material-icon-theme/icons ./icons

    # without the runtime the extension is a plain static icon theme
    jq 'del(.main, .browser, .activationEvents) | .contributes |= { iconThemes }' \
      package.json > package.json.tmp && mv package.json.tmp package.json
  '';
})
