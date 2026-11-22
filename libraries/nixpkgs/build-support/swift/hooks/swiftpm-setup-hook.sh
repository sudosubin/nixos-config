# shellcheck shell=bash

swiftpmSetupPostUnpackHook() {
    # fetchSwiftPMDeps links Packages/ and artifacts/ read-only, and packages patch them
    if [ -n "${swiftpmDeps-}" ]; then
        local deps="$NIX_BUILD_TOP/swiftpm-deps" dir
        mkdir "$deps"
        cp "$swiftpmDeps/workspace-state.json" "$deps/"
        for dir in Packages artifacts; do
            if [ -e "$swiftpmDeps/$dir" ]; then
                cp -r "$(realpath "$swiftpmDeps/$dir")" "$deps/$dir"
            fi
        done
        chmod -R u+w "$deps"
        swiftpmDeps="$deps"
    fi

    if [ -n "${swiftpmManifest-}" ]; then
        cp "$swiftpmManifest" "$NIX_BUILD_TOP/$sourceRoot/Package.swift"
    fi
}

swiftpmSetupPrePatchHook() {
    # swiftpmUnpackHook links the dependencies at Packages/Packages when the source has a Packages/
    if [ -L Packages/Packages ]; then
        rm Packages/Packages
        mv "$swiftpmDeps"/Packages/* Packages/
    fi
}

swiftpmSetupPostPatchHook() {
    # Resource bundle accessors fall back to the scratch path, so it must outlive the build
    : "${swiftpmScratchPath:=$out/libexec/swiftpm}"
    mkdir -p "$(dirname "$swiftpmScratchPath")" .build
    mv .build "$swiftpmScratchPath"
    ln -s "$swiftpmScratchPath" .build
    appendToVar swiftpmFlags --scratch-path "$swiftpmScratchPath"

    if [ -n "${swiftpmBuildSystem-}" ]; then
        appendToVar swiftpmFlags --build-system "$swiftpmBuildSystem"
    fi

    # apple-sdk's setup hook exports these, so they can only be overridden after setup
    if [ -n "${swiftpmSdk-}" ]; then
        export DEVELOPER_DIR="$swiftpmSdk" SDKROOT="$swiftpmSdk/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
    fi

    # swiftpmUnpackHook copies binary targets with cp -L, which breaks their framework symlinks
    if [ -d "${swiftpmDeps-}/artifacts" ]; then
        rm -rf .build/artifacts
        mv "$swiftpmDeps/artifacts" .build/
    fi

    # `#Preview` expands through PreviewsMacros, a plugin that ships only with Xcode
    if [ -z "${dontStripSwiftPreviews-}" ]; then
        (grep -rlZ --include='*.swift' '^[[:space:]]*#Preview\b' . || true) | xargs -0r @perl@ -0777 -pi -e \
            's/^([ \t]*#Preview\b[^{]*(\{(?:[^{}]++|(?2))*\}))/#if false\n$1\n#endif/gm'
    fi
}

# Keep only the resource bundles of the scratch path
swiftpmSetupPreFixupHook() {
    local binPath bundle scratch="$NIX_BUILD_TOP/swiftpm-scratch"
    binPath="$(swiftpmBinPath)"
    mv "$swiftpmScratchPath" "$scratch"
    rm -f .build
    rmdir "$(dirname "$swiftpmScratchPath")" 2>/dev/null || true
    for bundle in "$scratch/${binPath#"$swiftpmScratchPath"/}"/*.bundle; do
        if [ -e "$bundle" ]; then
            mkdir -p "$binPath"
            mv "$bundle" "$binPath/"
        fi
    done
}

# Must run before swiftpmUnpackHook, which vendors $swiftpmDeps and reads Package.swift
postUnpackHooks=(swiftpmSetupPostUnpackHook "${postUnpackHooks[@]}")
prePatchHooks+=(swiftpmSetupPrePatchHook)
postPatchHooks+=(swiftpmSetupPostPatchHook)
preFixupHooks+=(swiftpmSetupPreFixupHook)
