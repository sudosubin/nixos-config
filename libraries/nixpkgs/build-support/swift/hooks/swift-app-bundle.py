"""Assemble a macOS .app from a SwiftPM build and an Xcode target's build settings, the way Xcode would."""

import glob
import json
import os
import plistlib
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import openstep_plist

# Entitlements Xcode derives from build settings
ENTITLEMENT_SETTINGS = {
    "AUTOMATION_APPLE_EVENTS": "automation.apple-events",
    "ENABLE_RESOURCE_ACCESS_AUDIO_INPUT": "device.audio-input",
    "ENABLE_RESOURCE_ACCESS_CALENDARS": "personal-information.calendars",
    "ENABLE_RESOURCE_ACCESS_CAMERA": "device.camera",
    "ENABLE_RESOURCE_ACCESS_CONTACTS": "personal-information.addressbook",
    "ENABLE_RESOURCE_ACCESS_LOCATION": "personal-information.location",
    "ENABLE_RESOURCE_ACCESS_PHOTO_LIBRARY": "personal-information.photos-library",
    "RUNTIME_EXCEPTION_ALLOW_DYLD_ENVIRONMENT_VARIABLES": "cs.allow-dyld-environment-variables",
    "RUNTIME_EXCEPTION_ALLOW_JIT": "cs.allow-jit",
    "RUNTIME_EXCEPTION_ALLOW_UNSIGNED_EXECUTABLE_MEMORY": "cs.allow-unsigned-executable-memory",
    "RUNTIME_EXCEPTION_DEBUGGING_TOOL": "cs.debugger",
    "RUNTIME_EXCEPTION_DISABLE_EXECUTABLE_PAGE_PROTECTION": "cs.disable-executable-page-protection",
    "RUNTIME_EXCEPTION_DISABLE_LIBRARY_VALIDATION": "cs.disable-library-validation",
}


def build_settings():
    project = os.environ.get("xcodeProject") or sys.exit("swift-app-bundle: xcodeProject is not set")
    configuration = os.environ.get("xcodeConfiguration") or "Release"

    with open(Path(project) / "project.pbxproj") as f:
        objects = openstep_plist.load(f)["objects"]
    root = next(o for o in objects.values() if o["isa"] == "PBXProject")

    def configured(owner):
        configs = objects[owner["buildConfigurationList"]]["buildConfigurations"]
        return next(objects[c]["buildSettings"] for c in configs if objects[c]["name"] == configuration)

    targets = [objects[t] for t in root["targets"]]
    name = os.environ.get("xcodeTarget")
    if name:
        target = next(t for t in targets if t["name"] == name)
    else:
        (target,) = [t for t in targets if t.get("productType") == "com.apple.product-type.application"]

    return {
        "TARGET_NAME": target["name"],
        "PRODUCT_NAME": "$(TARGET_NAME)",
        "EXECUTABLE_NAME": "$(PRODUCT_NAME)",
        "PRODUCT_BUNDLE_PACKAGE_TYPE": "APPL",
        "DEVELOPMENT_LANGUAGE": "en",
        "MARKETING_VERSION": os.environ.get("version", "1.0"),
        "CURRENT_PROJECT_VERSION": "$(MARKETING_VERSION)",
    } | configured(root) | configured(target)


def expand(value, settings):
    """Expand $(VAR) and ${VAR}, ignoring modifiers like :rfc1034identifier."""
    if isinstance(value, str):
        return re.sub(r"\$[({](\w+)(?::[^)}]*)?[)}]", lambda m: expand(settings.get(m[1], ""), settings), value)
    if isinstance(value, list):
        return [expand(v, settings) for v in value]
    if isinstance(value, dict):
        return {k: expand(v, settings) for k, v in value.items()}
    return value


def compile_string_catalog(catalog, resources):
    """Compile an .xcstrings catalog into <lang>.lproj/<table>.strings."""
    tables = {}
    for key, entry in json.loads(catalog.read_text())["strings"].items():
        for lang, localization in entry.get("localizations", {}).items():
            if "stringUnit" in localization:
                tables.setdefault(lang, {})[key] = localization["stringUnit"]["value"]
    for lang, strings in tables.items():
        out = resources / f"{lang}.lproj/{catalog.stem}.strings"
        out.parent.mkdir(exist_ok=True)
        out.write_bytes(plistlib.dumps(strings))


def install(bin_path, patterns):
    settings = build_settings()
    get = lambda key: expand(settings.get(key, ""), settings)  # noqa: E731

    bin_path = Path(bin_path)
    build_top = Path(os.environ["NIX_BUILD_TOP"])
    contents = Path(os.environ["out"]) / "Applications" / f"{get('PRODUCT_NAME')}.app" / "Contents"
    resources = contents / "Resources"
    resources.mkdir(parents=True)
    (contents / "MacOS").mkdir()
    shutil.copy2(bin_path / get("EXECUTABLE_NAME"), contents / "MacOS")

    # Binary target frameworks, without what Xcode strips when embedding them
    for framework in bin_path.glob("*.framework"):
        dest = shutil.copytree(framework, contents / "Frameworks" / framework.name, symlinks=True)
        for path in [d / n for d in [dest, *dest.glob("Versions/*")] for n in ["Headers", "PrivateHeaders", "Modules"]]:
            shutil.rmtree(path) if path.is_dir() and not path.is_symlink() else path.unlink(missing_ok=True)

    # SwiftPM resource bundles
    for bundle in bin_path.glob("*.bundle"):
        shutil.copytree(bundle, resources / bundle.name, symlinks=True)

    asset_catalogs = []
    for pattern in patterns:
        for path in map(Path, sorted(glob.glob(pattern)) or sys.exit(f"swift-app-bundle: no match for {pattern}")):
            if path.suffix == ".xcassets":
                asset_catalogs.append(path)
            elif path.suffix == ".xcstrings":
                compile_string_catalog(path, resources)
            elif path.is_dir():
                shutil.copytree(path, resources / path.name, symlinks=True, dirs_exist_ok=True)
            else:
                shutil.copy2(path, resources)

    info = plistlib.loads(Path(get("INFOPLIST_FILE")).read_bytes()) if get("INFOPLIST_FILE") else {}
    if get("GENERATE_INFOPLIST_FILE") == "YES":
        for key, value in settings.items():
            if key.startswith("INFOPLIST_KEY_") and value != "":
                info.setdefault(key.removeprefix("INFOPLIST_KEY_"), {"YES": True, "NO": False}.get(value, value))
    info |= {
        "CFBundleDevelopmentRegion": "$(DEVELOPMENT_LANGUAGE)",
        "CFBundleExecutable": "$(EXECUTABLE_NAME)",
        "CFBundleIdentifier": "$(PRODUCT_BUNDLE_IDENTIFIER)",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundlePackageType": "$(PRODUCT_BUNDLE_PACKAGE_TYPE)",
        "CFBundleShortVersionString": "$(MARKETING_VERSION)",
        "CFBundleSupportedPlatforms": ["MacOSX"],
        "CFBundleVersion": "$(CURRENT_PROJECT_VERSION)",
    }
    info.setdefault("CFBundleName", "$(PRODUCT_NAME)")
    if get("MACOSX_DEPLOYMENT_TARGET"):
        info["LSMinimumSystemVersion"] = "$(MACOSX_DEPLOYMENT_TARGET)"

    if asset_catalogs:
        partial = build_top / "assetcatalog_generated_info.plist"
        args = ["actool", "--compile", resources, "--platform", "macosx", "--output-partial-info-plist", partial]
        if get("MACOSX_DEPLOYMENT_TARGET"):
            args += ["--minimum-deployment-target", get("MACOSX_DEPLOYMENT_TARGET")]
        if get("ASSETCATALOG_COMPILER_APPICON_NAME"):
            args += ["--app-icon", get("ASSETCATALOG_COMPILER_APPICON_NAME")]
        subprocess.run([*args, *asset_catalogs], check=True)
        info |= plistlib.loads(partial.read_bytes())

    (contents / "Info.plist").write_bytes(plistlib.dumps(expand(info, settings)))
    (contents / "PkgInfo").write_text(get("PRODUCT_BUNDLE_PACKAGE_TYPE") + "????")

    # For swiftAppBundleSign, which signs once fixup is done
    entitlements = plistlib.loads(expand(Path(get("CODE_SIGN_ENTITLEMENTS")).read_text(), settings).encode()) if get("CODE_SIGN_ENTITLEMENTS") else {}
    entitlements |= {f"com.apple.security.{key}": True for setting, key in ENTITLEMENT_SETTINGS.items() if get(setting) == "YES"}
    (build_top / "entitlements.plist").write_bytes(plistlib.dumps(entitlements))

    # Ad-hoc signatures default to a cdhash requirement, which voids TCC grants on every rebuild
    identifier = get("PRODUCT_BUNDLE_IDENTIFIER").encode()
    expr = struct.pack(">II", 2, len(identifier)) + identifier + b"\0" * (-len(identifier) % 4)
    (build_top / "requirement.bin").write_bytes(struct.pack(">III", 0xFADE0C00, 12 + len(expr), 1) + expr)


if __name__ == "__main__":
    install(sys.argv[1], sys.argv[2:])
