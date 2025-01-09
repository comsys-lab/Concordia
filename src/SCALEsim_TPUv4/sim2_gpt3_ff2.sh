#!/bin/bash
# Wait for each command to finish before executing the next command
# chmod +x run_sim.sh
# ./run_sim.sh
python3 run_gpt3_ff2.py gpt3_ff2 128x128 1x4 4
wait

python3 run_gpt3_ff2_bwd.py gpt3_ff2_bwd 128x128 1x4 4
wait