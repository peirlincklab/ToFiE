#!/bin/sh
# Usage: ./submit_pipeline.sh config_run1.yaml

set -e

CONFIG_FILE="${1:?Usage: ./submit_pipeline.sh <config.yaml>}"
[ -f "$CONFIG_FILE" ] || { echo "$CONFIG_FILE not found"; exit 1; }

TAG=$(basename "$CONFIG_FILE" .yaml)
mkdir -p logs outputs/logs

python generate_cluster_scripts.py --config_dir "$(pwd)/" --config_file "$CONFIG_FILE" --tag "$TAG"
chmod u+x "outputs/disperse_commands_${TAG}.sh"

jid1=$(sbatch --parsable --export=CONFIG_FILE="$CONFIG_FILE" --job-name="step1_${TAG}" step1_preprocess.sbatch)
jid2=$(sbatch --parsable --dependency=afterok:$jid1 --job-name="step2_${TAG}" "outputs/reconstruction_${TAG}.sh")
jid3=$(sbatch --parsable --dependency=afterok:$jid2 --export=CONFIG_FILE="$CONFIG_FILE" --job-name="step3_${TAG}" step3_postprocess.sbatch)
jid4=$(sbatch --parsable --dependency=afterany:$jid3 --job-name="sacct_${TAG}" \
    --time=00:05:00 --cpus-per-task=1 --mem-per-cpu=1G --ntasks=1 \
    --partition=compute-p2 --account=research-as-bn --output=logs/sacct_%j.out \
    --wrap="sacct -j $jid1,$jid2,$jid3 --format=JobID,JobName%20,Elapsed,TotalCPU,MaxRSS,MaxVMSize,AveCPU,AveRSS,NCPUS,ReqMem,State,ExitCode --units=M -p > outputs/logs/sacct_${TAG}_${jid1}_${jid2}_${jid3}.csv")

echo "[$TAG] step1=$jid1 step2=$jid2 step3=$jid3 sacct=$jid4"
