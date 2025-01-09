#!/bin/bash
# Wait for each command to finish before executing the next command
# chmod +x run_sim.sh
# ./run_sim.sh
python3 run_chinchilla_attention_head.py chinchilla_attention_head 128x128 1x4 2
wait

python3 run_chinchilla_attention_head_bwd.py chinchilla_attention_head_bwd 128x128 1x4 2
wait

python3 run_chinchilla_concat_linear.py chinchilla_concat_linear 128x128 1x4 2
wait

python3 run_chinchilla_concat_linear_bwd.py chinchilla_concat_linear_bwd 128x128 1x4 2
wait

python3 run_chinchilla_ff1.py chinchilla_ff1 128x128 1x4 2
wait

python3 run_chinchilla_ff1_bwd.py chinchilla_ff1_bwd 128x128 1x4 2
wait

python3 run_chinchilla_ff2.py chinchilla_ff2 128x128 1x4 2
wait

python3 run_chinchilla_ff2_bwd.py chinchilla_ff2_bwd 128x128 1x4 2
wait