#!/bin/bash
# Wait for each command to finish before executing the next command
# chmod +x run_sim.sh
# ./run_sim.sh
python3 run_t5_encoder_attention_head.py t5_encoder_attention_head 128x128 1x4 8
wait

python3 run_t5_encoder_attention_head_bwd.py t5_encoder_attention_head_bwd 128x128 1x4 8
wait

python3 run_t5_encoder_concat_linear.py t5_encoder_concat_linear 128x128 1x4 8
wait

python3 run_t5_encoder_concat_linear_bwd.py t5_encoder_concat_linear_bwd 128x128 1x4 8
wait

python3 run_t5_encoder_ff1.py t5_encoder_ff1 128x128 1x4 8
wait

python3 run_t5_encoder_ff1_bwd.py t5_encoder_ff1_bwd 128x128 1x4 8
wait

python3 run_t5_encoder_ff2.py t5_encoder_ff2 128x128 1x4 8
wait

python3 run_t5_encoder_ff2_bwd.py t5_encoder_ff2_bwd 128x128 1x4 8
wait