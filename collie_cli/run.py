import argparse
import os

import yaml
from torch.cuda import device_count, is_available

from .bullet import Bullet, Check, Input, VerticalPrompt, colors

description = "Launches an interactive instruction to create and save a launch script for CoLLiE. If the configuration file is not found or not specified, a new one will be saved at the given path, default to ./collie_default.yml. The launch script will be saved at the given path, default to ./run.sh."


def run_command_parser(subparsers=None):
    if subparsers is not None:
        parser = subparsers.add_parser("run")
    else:
        parser = argparse.ArgumentParser("CoLLiE run command")

    parser.usage = "collie run [<args>]"

    parser.add_argument(
        "--run_file",
        "-r",
        default="./run.sh",
        help="If `--run_file` is specified, the run script will be generated at the given path. Otherwise, the script will be generated at `./run.sh`.",
        type=str,
    )

    if subparsers is not None:
        parser.set_defaults(entrypoint=run_command_entry)
    return parser


def run_command_entry(args):
    raise NotImplementedError

    word_color = colors.foreground["cyan"]

    result = ""
    result += "#!/bin/bash\n"
    result += "# This script is generated by CoLLiE CLI.\n"
    result += "# You can modify this script to fit your needs.\n"
    result += "\n"

    # if is_available():
    #     device = Check(
    #         "Select CUDA devices",
    #         choices=list(range(device_count())),
    #         word_color=word_color,
    #     ).launch()
    #     device = ",".join([str(e) if b else "" for e, b in enumerate(device)])
    #     result += f"export CUDA_VISIBLE_DEVICES={device}\n"

    # method = Bullet(
    # "Select",
    # choices=["torchrun", "slurm"],
    # ).launch()
    # if method == "torchrun":

    result += "torchrun "
    result += f"--nproc_per_node={device_count()} "
    result += (
        f"{Input('Script path',default='main.py', word_color=word_color).launch()}\n"
    )

    with open(args.run_file, "w") as f:
        f.write(result)
        print(
            f"🎉 Script saved to {args.run_file}, use `sh {args.run_file}` to launch CoLLiE!"
        )
