import argparse, subprocess, sys
 
p = argparse.ArgumentParser()
p.add_argument("--config_dir", required=True)
p.add_argument("--config_file", default="config.yaml")
a = p.parse_args()
 
sys.path.append(a.config_dir)
from src.commands import get_skeleton_refinement_command
 
cmd = get_skeleton_refinement_command(a.config_dir, a.config_file)
print(cmd, flush=True)
subprocess.run(cmd, check=True)
