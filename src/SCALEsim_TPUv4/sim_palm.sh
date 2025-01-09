#!/bin/bash
# Wait for each command to finish before executing the next command
# chmod +x run_sim.sh
# ./run_sim.sh
python3 run_palm_attention_head.py palm_attention_head 128x128 1x4 2
wait

python3 run_palm_attention_head_bwd.py palm_attention_head_bwd 128x128 1x4 2
wait

python3 run_palm_concat_linear.py palm_concat_linear 128x128 1x4 2
wait

python3 run_palm_concat_linear_bwd.py palm_concat_linear_bwd 128x128 1x4 2
wait

python3 run_palm_ff1.py palm_ff1 128x128 1x4 2
wait

python3 run_palm_ff1_bwd.py palm_ff1_bwd 128x128 1x4 2
wait

python3 run_palm_ff2.py palm_ff2 128x128 1x4 2
wait

python3 run_palm_ff2_bwd.py palm_ff2_bwd 128x128 1x4 2
wait