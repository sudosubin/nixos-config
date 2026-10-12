# shellcheck shell=bash

swiftpmSetupPostUnpackHook() {
    # Copy the vendored dependencies so that they can be patched under Packages/
    if [ -n "${swiftpmDeps-}" ]; then
        cp -r "$swiftpmDeps" "$NIX_BUILD_TOP/swiftpm-deps"
        chmod -R u+w "$NIX_BUILD_TOP/swiftpm-deps"
        swiftpmDeps="$NIX_BUILD_TOP/swiftpm-deps"
    fi

    if [ -n "${swiftpmManifest-}" ]; then
        cp "$swiftpmManifest" "$NIX_BUILD_TOP/$sourceRoot/Package.swift"
    fi
}

swiftpmSetupPostPatchHook() {
    # swiftpmUnpackHook leaves out binary targets
    if [ -d "${swiftpmDeps-}/artifacts" ]; then
        mv "$swiftpmDeps/artifacts" .build/
        @jq@ --sort-keys --arg build "$PWD/.build/" \
            --slurpfile deps "$swiftpmDeps/workspace-state.json" \
            '.object.artifacts = [$deps[0].object.artifacts[] | .path = $build + .path]' \
            .build/workspace-state.json > .build/workspace-state.json~
        mv .build/workspace-state.json~ .build/workspace-state.json
    fi

    # `#Preview` expands through PreviewsMacros, a plugin that ships only with Xcode
    if [ -z "${dontStripSwiftPreviews-}" ]; then
        grep -rlZ --include='*.swift' '^[[:space:]]*#Preview\b' . | xargs -0r @perl@ -0777 -pi -e \
            's/^([ \t]*#Preview\b[^{]*(\{(?:[^{}]++|(?2))*\}))/#if false\n$1\n#endif/gm'
    fi
}

# Must run before swiftpmUnpackHook, which vendors $swiftpmDeps and reads Package.swift
postUnpackHooks=(swiftpmSetupPostUnpackHook "${postUnpackHooks[@]}")
postPatchHooks+=(swiftpmSetupPostPatchHook)
