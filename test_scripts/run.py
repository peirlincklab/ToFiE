#%%
import subprocess
import sys
import os
config_dir = r"C:\Users\rtogo\Nextcloud\Collagen\ToFiE-main\ToFiE-main\\"
config_file = "config.yaml"
config_path = os.path.join(config_dir, config_file)

sys.path.append(config_dir)
from src.commands import get_image_processing_command, get_disperse_commands, get_skeleton_refinement_command

def ToFiE_workflow(config_dir, config_file):

    """
    Step 1: Image processing
    """

    cmd = get_image_processing_command(config_dir, config_file)
    result = subprocess.run(cmd, capture_output=True, text=True)

    print("STDOUT:\n", result.stdout)
    print("STDERR:\n", result.stderr)
    print("Image processing is done!")


    """
    Step 2: Skeletonization using DisPerSe (via Docker locally)
    """

    cmd1, cmd2 = get_disperse_commands(config_dir, config_file)

    result1 = subprocess.run(cmd1, capture_output=True, text=True)

    print(result1.stdout)
    print(result1.stderr)

    if result1.returncode != 0:
        print("Error: First command failed.")
        exit(1)

    result2 = subprocess.run(cmd2, capture_output=True, text=True)

    print(result2.stdout)
    print(result2.stderr)

    if result2.returncode != 0:
        print("Error: Second command failed.")
        exit(1)

    print("Skeletonization by DisPerSe is completed!")


    """

    Step 3: Skeleton Refinement
    """
    cmd = get_skeleton_refinement_command(config_dir, config_file)
    result = subprocess.run(cmd, capture_output=True, text=True)

    print("STDOUT:\n", result.stdout)
    print("STDERR:\n", result.stderr)
    print("Skeleton refinement and graph construction is done!")



ToFiE_workflow(config_dir, config_file)



#%%
