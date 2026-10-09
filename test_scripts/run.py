"""
Run the full ToFiE workflow locally 
(Docker must be running)

python run.py
python run.py --config_dir /path/to/ToFiE --config_file config.yaml

"""
import argparse
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--config_dir", default=".", help="ToFiE folder (default: current folder)")
parser.add_argument("--config_file", default="config.yaml")
args = parser.parse_args()

sys.path.append(args.config_dir)
from src.commands import (
    get_image_processing_command,
    get_disperse_commands,
    get_skeleton_refinement_command,
)

# Step 1: image processing
cmd = get_image_processing_command(args.config_dir, args.config_file)
subprocess.run(cmd, check=True)
print("Image processing is done!")

# Step 2: skeletonization with DisPerSE (via Docker)
cmd1, cmd2 = get_disperse_commands(args.config_dir, args.config_file)
subprocess.run(cmd1, check=True)
subprocess.run(cmd2, check=True)
print("Skeletonization is done!")

# Step 3: skeleton refinement and graph construction
cmd = get_skeleton_refinement_command(args.config_dir, args.config_file)
subprocess.run(cmd, check=True)
print("Skeleton refinement and graph construction is done!")