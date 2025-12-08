#!/bin/sh

# Define directories
remote_dir=$6
container_dir="/home/"

# Set the directory for docker cache files in scratch
export APPTAINER_CACHEDIR=/scratch/$USER/.apptainer/cache

fits_filename=$1

# Parameters
persistence_val=$2
smooth_val=$3 
assemble_val=$4
trimBelow_val=$5

echo "=================="
echo "RUNNING PIPELINE"
echo "------------------"
echo "Remote Directory: $remote_dir"
echo "Fits Filename: $fits_filename"
echo "Persistence: $persistence_val"
echo "Smoothing: $smooth_val"
echo "Assemble: $assemble_val"
echo "Trimming: $trimBelow_val"
echo "=================="


# First command
if [ -f "${remote_dir}${1}.MSC" ]; then
	echo "Opening existing file ${remote_dir}${1}.MSC"
	command_to_run_1="mse ${container_dir}${fits_filename} -outDir ${container_dir} -upSkl -periodicity 0 -loadMSC ${container_dir}${1}.MSC -nthreads 8 -cut ${persistence_val}"
else
	command_to_run_1="mse ${container_dir}${fits_filename} -outDir ${container_dir} -upSkl -periodicity 0 -nthreads 8 -cut ${persistence_val}"
fi

apptainer exec --bind ${remote_dir}:${container_dir} disperse_latest.sif ${command_to_run_1}


if [ $? -ne 0 ]; then
    echo "Error: First command failed."
    exit 1
fi

# Check the output files of mse
echo "Output files:"
MSC_FILE="${1}.MSC"  #$(ls -t ${remote_dir} | head -n 3 | tail -n 1)
NDSKL_FILE="${1}_c${2}.up.NDskl" #$(ls -t ${remote_dir} | head -n 2 | tail -n 1)

echo "NDSKL_FILE: $NDSKL_FILE"
echo "MSC_FILE: $MSC_FILE"

# Second command
command_to_run_2="skelconv ${container_dir}${NDSKL_FILE} -outDir ${container_dir} -breakdown -smooth ${smooth_val} -assemble ${assemble_val} -trimBelow ${trimBelow_val} -rmBoundary -to NDskl_ascii"

apptainer exec --bind ${remote_dir}:${container_dir} disperse_latest.sif ${command_to_run_2}

if [ $? -ne 0 ]; then
    echo "Error: Second command failed."
    exit 1
fi
