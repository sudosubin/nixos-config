#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python310

import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_NIX_FILE = os.path.join(BASE_DIR, "libraries/nixpkgs/programs/cleanshot/default.nix")


def main():
    file_content = []
    package = get_package_info()

    with open(DEFAULT_NIX_FILE, "r") as f:
        file_content = f.readlines()

    for index, line in enumerate(file_content):
        if line.strip().startswith("version"):
            version = package["version"]
            file_content[index] = re.sub(r'".*"', rf'"{version}"', line)

        if line.strip().startswith("sha256"):
            sha256 = get_url_sha256(url=package["url"])
            file_content[index] = re.sub(r'".*"', rf'"{sha256}"', line)

    with open(DEFAULT_NIX_FILE, "w") as f:
        f.writelines(file_content)


def get_package_info() -> dict:
    import urllib.request

    url = "https://formulae.brew.sh/api/cask/cleanshot.json"

    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def get_url_sha256(url: str) -> str:
    import subprocess

    output = subprocess.check_output(["nix-prefetch-url", url])
    return output.decode().strip()


if __name__ == "__main__":
    main()
