#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python310

import json
import os
import re
import typing

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_NIX_FILE = os.path.join(BASE_DIR, "libraries/nixpkgs/programs/clop/default.nix")


def main():
    url = None
    file_content = []

    with open(DEFAULT_NIX_FILE, "r") as f:
        file_content = f.readlines()

    for index, line in enumerate(file_content):
        if line.strip().startswith("version"):
            version = get_package_version()
            file_content[index] = re.sub(r'".*"', rf'"{version}"', line)

        if line.strip().startswith("url"):
            if match := re.match(r'.*"(.*)".*', line):
                url = match.group(1)

        if line.strip().startswith("sha256") and url:
            sha256 = get_url_sha256(url=url)
            file_content[index] = re.sub(r'".*"', rf'"{sha256}"', line)

    with open(DEFAULT_NIX_FILE, "w") as f:
        f.writelines(file_content)


def get_package_version() -> typing.Optional[str]:
    import urllib.request

    url = "https://raw.githubusercontent.com/FuzzyIdeas/Clop/main/Clop.xcodeproj/project.pbxproj"

    with urllib.request.urlopen(url, timeout=10) as r:
        if match := re.match(r".*MARKETING_VERSION = ([1-9\.]*);.*", "".join(r.read().decode().splitlines())):
            return match.group(1)


def get_url_sha256(url: str) -> str:
    import subprocess

    output = subprocess.check_output(["nix-prefetch-url", url])
    return output.decode().strip()


if __name__ == "__main__":
    main()
