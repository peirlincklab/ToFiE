import os
import yaml
from pathlib import Path


def get_image_processing_command(config_dir,  config_path):
        
    cmd = [
        "python",
        config_dir + "src/image_processing.py",
        "--config", config_path,
    ]

    return cmd

def get_disperse_commands(config_dir, config_path, local=True):
        
    with open(config_path) as f:
        config = yaml.safe_load(f)

    base_path = Path(config["path"])
    local_dir = str(base_path / config["path_to_output"].strip("/"))  + "/"
    remote_dir = Path(config["remote_dir"])
    container_dir = "/home/"
    docker_image = "glyg/disperse:latest"
    fits_filename = "processed_" + config["image"] + ".fits"

    print ("input: ", fits_filename, ", output: ", local_dir)

    persistence_val = config["persistence_val"]
    smooth_val = config["smooth_val"]
    assemble_val = config["assemble_val"]
    trimBelow_val = config["trimBelow_val"]

    msc_file_path = os.path.join(local_dir, f"{fits_filename}.MSC")

    # If DisPerse is to be run on the cluster, create a bash script instead.
    if local == False:

        # Make a bash script for running step 2 on the cluster.
        def create_bash_file(template_path, output_path, **kwargs):
            with open(template_path, 'r') as f:
                script = f.read()

            for key, value in kwargs.items():
                script = script.replace(f"{{{{{key}}}}}", str(value))

            with open(output_path, 'w') as f:
                f.write(script)

            print(f"Created bash script: {output_path}")

        create_bash_file(config_dir + "template_reconstruction.sh", config_dir + "outputs/reconstruction.sh", fits_filename= fits_filename, sample_dir =remote_dir, persistence_val=persistence_val, smooth_val=smooth_val, assemble_val=assemble_val, trimBelow_val=trimBelow_val)
        create_bash_file(config_dir + "template_disperse_commands.sh", config_dir + "outputs/disperse_commands.sh")
        
        return
    
    if local == True:

        # First command
        if os.path.isfile(msc_file_path):
            print(f"Opening existing file {msc_file_path}")
            command_to_run_1 = f"mse {container_dir}{fits_filename} -outDir {container_dir} -upSkl -periodicity 0 -loadMSC {container_dir}{fits_filename}.MSC -nthreads 8 -cut {persistence_val}"
        else:
            command_to_run_1 = f"mse {container_dir}{fits_filename} -outDir {container_dir} -upSkl -periodicity 0 -nthreads 8 -cut {persistence_val}"

        docker_cmd_1 = [
            "docker", "run", "--rm",
            "--platform=linux/amd64",
            "-v", f"{local_dir}:{container_dir}",
            docker_image,  
            "/bin/sh", "-c", command_to_run_1
        ]

        # Filenames
        MSC_FILE = f"{fits_filename}.MSC"
        NDSKL_FILE = f"{fits_filename}_c{persistence_val}.up.NDskl"
        print(f"Output files:\nMSC_FILE: {MSC_FILE}\nNDSKL_FILE: {NDSKL_FILE}")

        # Second command
        command_to_run_2 = f"skelconv {container_dir}{NDSKL_FILE} -outDir {container_dir} -breakdown -smooth {smooth_val} -assemble {assemble_val} -trimBelow {trimBelow_val} -rmBoundary -to NDskl_ascii"

        docker_cmd_2 = [
            "docker", "run", "--rm",
            "--platform=linux/amd64",
            "-v", f"{local_dir}:{container_dir}",
            docker_image,
            "/bin/sh", "-c", command_to_run_2
        ]

        return docker_cmd_1, docker_cmd_2


def get_skeleton_refinement_command(config_dir, config_path):
        
    cmd = [
        "python",
        config_dir + "src/skeleton_refinement.py",
        "--config", config_path, 
    ]
    
    return cmd