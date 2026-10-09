#!/bin/bash
#SBATCH --job-name=step3
#SBATCH --time=04:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-cpu=3G
#SBATCH --partition=compute-p2
#SBATCH --account=research-as-bn
#SBATCH --output=logs/step3_%j.out

module load 2026 cpu miniforge3
conda activate /scratch/$USER/ToFiE_env

D=/scratch/rtogo/ToFiE
CONFIG_FILE="${CONFIG_FILE:-config.yaml}"
echo "Using config file: $CONFIG_FILE"

python -u $D/run_step3.py --config_dir $D --config_file "${CONFIG_FILE:-config.yaml}"
