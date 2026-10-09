import os
import sys
import yaml
from pathlib import Path

python_exe = sys.executable


def get_image_processing_command(config_dir, config_file):
    return [python_exe, str(Path(config_dir) / "src" / "image_processing.py"),
            "--config", str(Path(config_dir) / config_file)]


def get_skeleton_refinement_command(config_dir, config_file):
    return [python_exe, str(Path(config_dir) / "src" / "skeleton_refinement.py"),
            "--config", str(Path(config_dir) / config_file)]


def get_disperse_commands(config_dir, config_file):
    with open(os.path.join(config_dir, config_file)) as f:
        config = yaml.safe_load(f)

    fits = "processed_" + config["image"] + ".fits"
    pers = config["persistence_val"]
    nthreads = config.get("nthreads_val", 8)
    c = "/home/"
    local_dir = str(Path(config["path"]) / config["path_to_output"].strip("/")) + "/"

    load = f"-loadMSC {c}{fits}.MSC " if os.path.isfile(f"{local_dir}{fits}.MSC") else ""
    cmd1 = f"mse {c}{fits} -outDir {c} -upSkl -periodicity 0 {load}-nthreads {nthreads} -cut {pers}"
    cmd2 = (f"skelconv {c}{fits}_c{pers}.up.NDskl -outDir {c} -breakdown "
            f"-smooth {config['smooth_val']} -assemble {config['assemble_val']} "
            f"-trimBelow {config['trimBelow_val']} -rmBoundary -to NDskl_ascii")

    docker = ["docker", "run", "--rm", "--platform=linux/amd64", "-v", f"{local_dir}:{c}",
              "glyg/disperse:latest", "/bin/sh", "-c"]
    return docker + [cmd1], docker + [cmd2]