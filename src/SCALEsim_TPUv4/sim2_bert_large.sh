#!/bin/bash
# Wait for each command to finish before executing the next command
# chmod +x run_sim.sh
# ./run_sim.sh
python3 run_bert_large_attention_head.py bert_large_attention_head 128x128 1x4 64
wait

python3 run_bert_large_attention_head_bwd.py bert_large_attention_head_bwd 128x128 1x4 64
wait

python3 run_bert_large_concat_linear.py bert_large_concat_linear 128x128 1x4 64
wait

python3 run_bert_large_concat_linear_bwd.py bert_large_concat_linear_bwd 128x128 1x4 64
wait

python3 run_bert_large_ff1.py bert_large_ff1 128x128 1x4 64
wait

python3 run_bert_large_ff1_bwd.py bert_large_ff1_bwd 128x128 1x4 64
wait

python3 run_bert_large_ff2.py bert_large_ff2 128x128 1x4 64
wait

python3 run_bert_large_ff2_bwd.py bert_large_ff2_bwd 128x128 1x4 64
wait