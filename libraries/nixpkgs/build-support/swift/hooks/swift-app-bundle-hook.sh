# shellcheck shell=bash

swiftAppBundleInstallPhase() {
    runHook preInstall

    # Structured attrs are not exported to child processes
    export xcodeProject xcodeTarget xcodeConfiguration version

    local resourcesArray=()
    concatTo resourcesArray appResources
    @swiftAppBundle@ "$(swiftpmBinPath)" "${resourcesArray[@]}"

    runHook postInstall
}

# Like Xcode's swift-stdlib-tool, embed the libraries loaded through rpaths into
# the Nix store (Swift back-deployment libraries), then drop those rpaths
swiftAppBundleFixupRpaths() {
    local exe rpath lib
    for exe in "$out"/Applications/*.app/Contents/MacOS/*; do
        for rpath in $(otool -l "$exe" | awk -v store="$NIX_STORE/" '$1 == "path" && index($2, store) == 1 { print $2 }'); do
            for lib in $(otool -L "$exe" | awk '$1 ~ /^@rpath\// { print substr($1, 8) }'); do
                if [ -e "$rpath/$lib" ]; then
                    install -Dm755 "$rpath/$lib" "${exe%/MacOS/*}/Frameworks/$lib"
                fi
            done
            install_name_tool -delete_rpath "$rpath" "$exe"
        done
    done
}

swiftAppBundleSign() {
    local flagsArray=(--code-signature-flags runtime)
    if [ -f "$NIX_BUILD_TOP/entitlements.plist" ]; then
        flagsArray+=(--entitlements-xml-file "$NIX_BUILD_TOP/entitlements.plist")
    fi
    for app in "$out"/Applications/*.app; do
        rcodesign sign "${flagsArray[@]}" "$app"
    done
}

appendToVar swiftpmFlags -Xlinker -rpath -Xlinker @executable_path/../Frameworks

# swiftpmHook may have set its installPhase first
if [ -z "${dontUseSwiftAppBundleInstall-}" ] && [[ -z "${installPhase-}" || "$installPhase" == swiftpmInstallPhase ]]; then
    installPhase=swiftAppBundleInstallPhase
fi

# Run after strip and swift's rpath rewrites, signing last
postFixupHooks+=(swiftAppBundleFixupRpaths swiftAppBundleSign)
