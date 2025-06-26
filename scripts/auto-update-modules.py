#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python313 python313Packages.aiofiles python313Packages.pyyaml

import asyncio
import logging
import os
import re
import sys

import aiofiles  # pyright: ignore [reportMissingModuleSource]
import yaml  # pyright: ignore [reportMissingModuleSource]

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))


class Workload:
    config_file_path = f"{ROOT_DIR}/scripts/auto-update-modules.yaml"

    async def run(self):
        config = await self.read_config()
        futures = [self.update_module(module) for module in config["modules"]]
        await asyncio.gather(*futures)

    async def update_module(self, module):
        module_path = os.path.abspath(f"{ROOT_DIR}/{module['path']}")
        module_lines = []

        async with aiofiles.open(module_path, mode="r") as f:
            module_lines = await f.readlines()

        module_args = {}
        for arg in module["args"]["read_from_method"]:
            module_args[arg] = await self.execute(module["methods"][f"get_{arg}"])

        for index, module_line in enumerate(module_lines):
            for arg in module["args"]["read_from_file"]:
                if module_line.strip().startswith(arg):
                    if match := re.match(r'.*"(.*)".*', module_line):
                        module_args[arg] = match.group(1)

                        # hard-coded `url` fixer, `sha256` replacer
                        if arg == "url":
                            module_args["url"] = module_args["url"].replace(
                                "${version}", module_args["version"]
                            )
                            module_args["sha256"] = await self.calculate_sha256(
                                module_args["url"]
                            )

            for arg in module["args"]["write"]:
                if module_line.strip().startswith(arg):
                    module_lines[index] = re.sub(
                        r'".*"', rf'"{module_args[arg]}"', module_line
                    )

        async with aiofiles.open(module_path, mode="w") as f:
            await f.writelines(module_lines)

        logger.info(f"- updated {module['path']}")

    async def execute(self, cmd: str):
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        return stdout.decode().strip()

    async def calculate_sha256(self, url: str):
        return await self.execute(f"nix-prefetch-url {url}")

    async def read_config(self):
        async with aiofiles.open(self.config_file_path, mode="r") as f:
            content = await f.read()
            return yaml.safe_load(content)


if __name__ == "__main__":
    logger.setLevel("INFO")
    asyncio.run(Workload().run())
