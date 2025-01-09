#!/bin/bash
# Wait for each command to finish before executing the next command
# chmod +x run_sim.sh
# ./run_sim.sh
python3 run_gpt3_attention_head.py gpt3_attention_head 128x128 1x4 4
wait

python3 run_gpt3_attention_head_bwd.py gpt3_attention_head_bwd 128x128 1x4 4
wait

python3 run_gpt3_concat_linear.py gpt3_concat_linear 128x128 1x4 4
wait

python3 run_gpt3_concat_linear_bwd.py gpt3_concat_linear_bwd 128x128 1x4 4
wait