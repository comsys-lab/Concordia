#!/bin/bash
# Wait for each command to finish before executing the next command
# chmod +x run_sim.sh
# ./run_sim.sh
python3 run_palm_ff1.py palm_ff1 128x128 1x4 4
wait

python3 run_palm_ff1_bwd.py palm_ff1_bwd 128x128 1x4 4
wait
