"""Assemble a macOS .app from a SwiftPM build, the way Xcode would.

Bundle metadata comes from the build settings of an Xcode project target
($xcodeProject, $xcodeTarget, $xcodeConfiguration).
"""

import glob
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

import openstep_plist


def build_settings():
    project = os.environ.get("xcodeProject")
    if not project:
        sys.exit("swift-app-bundle: xcodeProject is not set")
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

    settings = {
        "TARGET_NAME": target["name"],
        "PRODUCT_NAME": "$(TARGET_NAME)",
        "EXECUTABLE_NAME": "$(PRODUCT_NAME)",
        "PRODUCT_BUNDLE_PACKAGE_TYPE": "APPL",
        "DEVELOPMENT_LANGUAGE": "en",
        "MARKETING_VERSION": os.environ.get("version", "1.0"),
        "CURRENT_PROJECT_VERSION": "$(MARKETING_VERSION)",
    }
    settings |= configured(root) | configured(target)
    return settings


def expand(value, settings):
    """Expand $(VAR) and ${VAR} references, ignoring modifiers like :rfc1034identifier."""
    if isinstance(value, str):
        return re.sub(
            r"\$[({](\w+)(?::[^)}]*)?[)}]",
            lambda m: expand(settings.get(m[1], ""), settings),
            value,
        )
    if isinstance(value, list):
        return [expand(v, settings) for v in value]
    if isinstance(value, dict):
        return {k: expand(v, settings) for k, v in value.items()}
    return value


def plist_value(value):
    return {"YES": True, "NO": False}.get(value, value)


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
    app = Path(os.environ["out"]) / "Applications" / f"{get('PRODUCT_NAME')}.app"
    contents = app / "Contents"
    resources = contents / "Resources"
    resources.mkdir(parents=True)

    executable = contents / "MacOS" / get("EXECUTABLE_NAME")
    executable.parent.mkdir()
    shutil.copy2(bin_path / get("EXECUTABLE_NAME"), executable)

    # Binary target frameworks, without what Xcode strips when embedding them
    for framework in bin_path.glob("*.framework"):
        dest = contents / "Frameworks" / framework.name
        shutil.copytree(framework, dest, symlinks=True)
        for d in [dest, *dest.glob("Versions/*")]:
            for name in ["Headers", "PrivateHeaders", "Modules"]:
                path = d / name
                if path.is_symlink() or path.is_file():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path)

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

    info = {}
    if get("INFOPLIST_FILE"):
        info = plistlib.loads(Path(get("INFOPLIST_FILE")).read_bytes())
    if get("GENERATE_INFOPLIST_FILE") == "YES":
        for key, value in settings.items():
            if key.startswith("INFOPLIST_KEY_") and value != "":
                info.setdefault(key.removeprefix("INFOPLIST_KEY_"), plist_value(value))
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
        partial = Path(os.environ["NIX_BUILD_TOP"]) / "assetcatalog_generated_info.plist"
        args = ["actool", "--compile", resources, "--platform", "macosx", "--output-partial-info-plist", partial]
        if get("MACOSX_DEPLOYMENT_TARGET"):
            args += ["--minimum-deployment-target", get("MACOSX_DEPLOYMENT_TARGET")]
        if get("ASSETCATALOG_COMPILER_APPICON_NAME"):
            args += ["--app-icon", get("ASSETCATALOG_COMPILER_APPICON_NAME")]
        subprocess.run([*args, *asset_catalogs], check=True)
        info |= plistlib.loads(partial.read_bytes())

    (contents / "Info.plist").write_bytes(plistlib.dumps(expand(info, settings)))
    (contents / "PkgInfo").write_text(get("PRODUCT_BUNDLE_PACKAGE_TYPE") + "????")

    # For swiftAppBundleSignHook, which signs once fixup is done
    if get("CODE_SIGN_ENTITLEMENTS"):
        entitlements = Path(os.environ["NIX_BUILD_TOP"]) / "entitlements.plist"
        entitlements.write_text(expand(Path(get("CODE_SIGN_ENTITLEMENTS")).read_text(), settings))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: swift-app-bundle <bin-path> [resource...]")
    install(sys.argv[1], sys.argv[2:])
