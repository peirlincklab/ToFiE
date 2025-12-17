#!/bin/sh
#
#SBATCH --job-name="3D reconstruction" 
#SBATCH --time=100:00:00 
#SBATCH --ntasks=1 
#SBATCH --account=research-as-bn 
#SBATCH --cpus-per-task=6 
#SBATCH --partition=compute-p2
#SBATCH --mem-per-cpu=16G
#SBATCH --output=output_%j.out

module load apptainer

chmod u+x disperse_commands.sh

srun disperse_commands.sh {{fits_filename}} {{persistence_val}} {{smooth_val}} {{assemble_val}} {{trimBelow_val}} {{sample_dir}}}
