#!/bin/sh
# usage: disperse_commands.sh fits persistence smooth assemble trimBelow remote_dir nthreads
set -e

fits=$1
pers=$2
smooth=$3
assemble=$4
trim=$5
remote_dir=$6
nthreads=$7

c=/home/
sif=disperse_latest.sif
export APPTAINER_CACHEDIR=/scratch/$USER/.apptainer/cache

mkdir -p "${remote_dir}logs"
log="${remote_dir}logs/timing_${SLURM_JOB_ID:-manual}.csv"
[ -f "$log" ] || echo "step,wall_s,max_rss_kb,pct_cpu,exit" > "$log"

load=""
[ -f "${remote_dir}${fits}.MSC" ] && load="-loadMSC ${c}${fits}.MSC"

/usr/bin/time -a -o "$log" -f "mse,%e,%M,%P,%x" \
    apptainer exec --bind ${remote_dir}:${c} $sif \
    mse ${c}${fits} -outDir $c -upSkl -periodicity 0 $load -nthreads $nthreads -cut $pers

/usr/bin/time -a -o "$log" -f "skelconv,%e,%M,%P,%x" \
    apptainer exec --bind ${remote_dir}:${c} $sif \
    skelconv ${c}${fits}_c${pers}.up.NDskl -outDir $c -breakdown -smooth $smooth -assemble $assemble -trimBelow $trim -rmBoundary -to NDskl_ascii
