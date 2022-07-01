#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python310

import json
import logging
import os
import re
import sys
import typing
from dataclasses import dataclass

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_NIX_FILE = os.path.join(CURRENT_DIR, "default.nix")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))


@dataclass
class VscodeExtension:
    name: str = ""
    publisher: str = ""
    version: str = ""
    sha256: str = ""

    def is_valid(self):
        return self.name and self.publisher and self.version and self.sha256


def main():
    logger.setLevel("INFO")

    file_content = []
    vscode_extension = VscodeExtension()

    with open(DEFAULT_NIX_FILE, "r") as f:
        file_content = f.readlines()

    for index, line in enumerate(file_content):
        if line.strip().startswith("name"):
            vscode_extension.name = parse_line(line)

        if line.strip().startswith("publisher"):
            vscode_extension.publisher = parse_line(line)

        if line.strip().startswith("version"):
            vscode_extension.version = parse_line(line)

        if line.strip().startswith("sha256"):
            vscode_extension.sha256 = parse_line(line)

        if vscode_extension.is_valid():
            logger.info(f"fetching {vscode_extension.publisher}.{vscode_extension.name}")
            version, sha256 = get_extension_info(name=vscode_extension.name, publisher=vscode_extension.publisher)

            # replace version
            file_content[index - 1] = file_content[index - 1].replace(vscode_extension.version, version)

            # replace sha256
            file_content[index] = file_content[index].replace(vscode_extension.sha256, sha256)

            vscode_extension = VscodeExtension()

    with open(DEFAULT_NIX_FILE, "w") as f:
        f.writelines(file_content)


def parse_line(line: str) -> str:
    return re.sub("[\";]", "", line.split("=", maxsplit=1)[1]).strip()


def get_extension_info(*, name: str, publisher: str) -> typing.Tuple[str, str]:
    import tempfile
    import urllib.request

    url = f"https://{publisher}.gallery.vsassets.io/_apis/public/gallery/publisher/{publisher}/extension/{name}/latest/assetbyname/Microsoft.VisualStudio.Services.VSIXPackage"

    with urllib.request.urlopen(url, timeout=10) as d, tempfile.NamedTemporaryFile(suffix=".zip") as f:
        f.write(d.read())

        version = get_extension_version(f.name)
        sha256 = get_extension_sha256(f.name)

    return version, sha256


def get_extension_version(extension_dir: str) -> str:
    import shutil
    import tempfile
    import zipfile

    extract_dir = tempfile.mkdtemp()
    package_json_dir = os.path.join(extract_dir, "extension/package.json")

    with zipfile.ZipFile(extension_dir, 'r') as z:
        z.extractall(extract_dir)

    with open(package_json_dir, mode="r") as f:
        package_json = json.load(f)
        version = package_json['version']

    shutil.rmtree(extract_dir)

    return version


def get_extension_sha256(extension_dir: str) -> str:
    import subprocess

    output = subprocess.check_output( ["nix-hash", "--flat", "--base32", "--type", "sha256", extension_dir])
    return output.decode().strip()


if __name__ == "__main__":
    main()
