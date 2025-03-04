import math
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import csv
from datetime import datetime

from scalesim.compute.operand_matrix import operand_matrix as opmat
from scalesim.topology_utils import topologies
from scalesim.scale_config import scale_config

from scalesim.compute.systolic_compute_os import systolic_compute_os
from scalesim.compute.systolic_compute_ws_faster import systolic_compute_ws
from scalesim.compute.systolic_compute_is import systolic_compute_is
from scalesim.memory.double_buffered_scratchpad_mem_faster import double_buffered_scratchpad as mem_dbsp

import os

def createDirectory(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print("Error: Failed to create the directory.")

def mkcfg(config_base, dataflow, SArow, SAcol, IF_SRAM, Fil_SRAM, OF_SRAM):
    createDirectory(config_base)
    cfgfname = 'tmtraining_tpuv4_1x4'
    cfgname = config_base + cfgfname +'.cfg'
    
    num_pod = int((128/int(SArow)) * (128/int(SAcol)))
    Arr_H = int(SArow)
    Arr_W = int(SAcol)
    IF_SRAM = int(input_SRAM/num_pod) 
    Fil_SRAM = int(weight_SRAM/num_pod) 
    OF_SRAM = int(output_SRAM/num_pod)
    
    fwrite=open(cfgname,'w')

    #make cfg file
    fwrite.write('\
    [general]\n\
    run_name = tmtraining_tpuv4_1x4\n\
    \n\
    [architecture_presets]\n\
    ArrayHeight:    {}\n\
    ArrayWidth:     {}\n\
    IfmapSramSzkB:    {}\n\
    FilterSramSzkB:   {}\n\
    OfmapSramSzkB:    {}\n\
    IfmapOffset:    0\n\
    FilterOffset:   10000000\n\
    OfmapOffset:    20000000\n\
    Dataflow : {}\n\
    Bandwidth : 10\n\
    MemoryBanks: 1\n\
    \n\
    [run_presets]\n\
    InterfaceBandwidth: CALC'.format(Arr_H, Arr_W, IF_SRAM, Fil_SRAM, OF_SRAM, dataflow))
    fwrite.close()
    
    return cfgfname, cfgname


class scaled_out_simulator:
    def __init__(self):
        self.topo_obj = topologies()
        self.single_arr_cfg = scale_config()

        self.grid_rows = 1
        self.grid_cols = 1
        self.dataflow = 'os'

        # Stats objects
        self.stats_compute_cycles = np.ones(1) * -1
        self.stats_ifmap_dram_reads = np.ones(1) * -1
        self.stats_ifmap_dram_start_cycl = np.ones(1) * -1
        self.stats_ifmap_dram_end_cycl = np.ones(1) * -1

        self.stats_filter_dram_reads = np.ones(1) * -1
        self.stats_filter_dram_start_cycl = np.ones(1) * -1
        self.stats_filter_dram_end_cycl = np.ones(1) * -1

        self.stats_ofmap_dram_reads = np.ones(1) * -1
        self.stats_ofmap_dram_start_cycl = np.ones(1) * -1
        self.stats_ofmap_dram_end_cycl = np.ones(1) * -1

        self.overall_compute_cycles_per_layers = []
        self.overall_util_perc_per_layer = []

        self.overall_compute_cycles_all_layers = 0
        self.overall_util_perc_all_layer = 0

        self.total_ifmap_dram_reads = []
        self.total_filter_dram_reads = []
        self.total_ofmap_dram_writes = []

        # Added: SRAM
        self.stats_ifmap_sram_reads = np.ones(1) * -1
        self.stats_filter_sram_reads = np.ones(1) * -1
        self.stats_ofmap_sram_writes = np.ones(1) * -1

        self.total_ifmap_sram_reads = []
        self.total_filter_sram_reads = []
        self.total_ofmap_sram_writes = []

        # For new utilization (mapping eff & pod eff)
        self.OVER_util = []
        self.POD_util = []

        # Flags
        self.params_valid = False
        self.all_grids_done = False
        self.metrics_ready = False
        
        # Flags and Vars for faster simulation
        self.get_input_dram = False
        self.get_weight_dram = False
        self.input_dram_list = []
        self.weight_dram_list = []
    
    #
    def init_faster_flags(self):
        # Flags and Vars for faster simulation
        self.get_input_dram = False
        self.get_weight_dram = False
        self.input_dram_list = []
        self.weight_dram_list = []

    #
    def set_params(self,
                    topology_filename='./files/tutorial3_topofile.csv',
                    single_arr_config_file='./files/single_arr_config.cfg',
                    grid_rows=1, grid_cols=1,
                    dataflow = 'os',
                    mnk_input= False,
                    batch_size=1
                    ):

        # Blank 1. Read the input files 
        self.topo_obj = topologies()
        self.topo_obj.load_arrays(topology_filename, mnk_inputs=mnk_input)
        num_layers=self.topo_obj.get_num_layers()

        self.single_arr_cfg = scale_config()
        self.single_arr_cfg.read_conf_file(single_arr_config_file)

        self.grid_rows = grid_rows
        self.grid_cols = grid_cols

        num_arrays = grid_rows * grid_cols
        self.stats_compute_cycles = np.ones((num_layers, num_arrays)) * -1
        #

        self.stats_ifmap_dram_reads = np.ones((num_layers, num_arrays)) * -1
        self.stats_ifmap_dram_start_cycl = np.ones((num_layers, num_arrays)) * -1
        self.stats_ifmap_dram_end_cycl = np.ones((num_layers, num_arrays)) * -1

        self.stats_filter_dram_reads = np.ones((num_layers, num_arrays)) * -1
        self.stats_filter_dram_start_cycl = np.ones((num_layers, num_arrays)) * -1
        self.stats_filter_dram_end_cycl = np.ones((num_layers, num_arrays)) * -1

        self.stats_ofmap_dram_writes = np.ones((num_layers, num_arrays)) * -1
        self.stats_ofmap_dram_start_cycl = np.ones((num_layers, num_arrays)) * -1
        self.stats_ofmap_dram_end_cycl = np.ones((num_layers, num_arrays)) * -1

        self.total_ifmap_dram_reads = []
        self.total_filter_dram_reads = []
        self.total_ofmap_dram_writes = []

        # For SRAM
        self.stats_ifmap_sram_reads = np.ones((num_layers, num_arrays)) * -1
        self.stats_filter_sram_reads = np.ones((num_layers, num_arrays)) * -1
        self.stats_ofmap_sram_writes = np.ones((num_layers, num_arrays)) * -1

        self.total_ifmap_sram_reads = []
        self.total_filter_sram_reads = []
        self.total_ofmap_sram_writes = []
        #

        # For Batch config
        self.batch_sz = batch_size
        # Runtime, Cutil
        self.m_dim = 0
        self.n_dim = 0
        self.k_dim = 0
        #

        self.overall_compute_cycles_per_layers = []
        self.overall_util_perc_per_layer = []

        self.overall_compute_cycles_all_layers = 0
        self.overall_util_perc_all_layer = 0

        self.dataflow = dataflow
        self.params_valid = True

    #
    def run_simulation_single_layer(self, layer_id=0):

        opmat_obj = opmat()
        opmat_obj.set_params(config_obj=self.single_arr_cfg, topoutil_obj=self.topo_obj, layer_id=layer_id, batch_size=self.batch_sz)

        _, ifmap_op_mat = opmat_obj.get_ifmap_matrix()
        # print('ifmap_op_mat: {}'.format(ifmap_op_mat.shape)) #DEBUG
        _, filter_op_mat = opmat_obj.get_filter_matrix()
        _, ofmap_op_mat = opmat_obj.get_ofmap_matrix()
        # print('ofmap_op_mat: {}'.format(ofmap_op_mat.shape)) #DEBUG

        #
        self.init_faster_flags()
        
        #
        SA_row, SA_col = self.single_arr_cfg.get_array_dims()
        SR=ifmap_op_mat.shape[0] # Not used
        SC=filter_op_mat.shape[1] # Not used
        #

        PE_util_this_layer=[]

        # determine used_row and used_col
        if_per_tile = np.ceil(ifmap_op_mat.shape[0]/self.grid_rows)
        temp = ifmap_op_mat.shape[0]
        Used_row=0
        for i in range(self.grid_rows):
            Used_row = Used_row + 1
            temp = temp - if_per_tile
            if temp <= 0:
                break
        fil_per_tile = np.ceil(filter_op_mat.shape[1]/self.grid_cols)
        temp = filter_op_mat.shape[1]
        Used_col=0
        for i in range(self.grid_cols):
            Used_col = Used_col + 1
            temp = temp - fil_per_tile
            if temp <= 0:
                break
        #

        # Get Pod utilization
        pod_util_this_layer = (Used_row * Used_col) / (self.grid_rows * self.grid_cols)
        assert pod_util_this_layer <= 1.0, "pod is bigger than 1.0"
        self.POD_util.append(pod_util_this_layer)
        #

        for grid_row_id in range(self.grid_rows):
            for grid_col_id in range(self.grid_cols):

                if (grid_row_id >= Used_row) | (grid_col_id >= Used_col):
                    continue
                
                # For faster simulation
                if grid_col_id == 0:
                    self.get_input_dram = True
                else:
                    self.get_input_dram = False
                    
                if grid_row_id == 0:
                    self.get_weight_dram = True
                else:
                    self.get_weight_dram = False
                #
                
                arr_id = grid_row_id * self.grid_cols + grid_col_id 
                print('Running subarray ' + str(arr_id))

                ifmap_op_mat_part, filter_op_mat_part, ofmap_op_mat_part =\
                    self.get_opmat_parts(ifmap_op_mat, filter_op_mat, ofmap_op_mat,
                                         grid_row_id, grid_col_id)

                # Skip empty operand matrices
                if ifmap_op_mat_part.shape[0]*ifmap_op_mat_part.shape[1]==0 or\
                    filter_op_mat_part.shape[0]*filter_op_mat_part.shape[1]==0 or\
                        ofmap_op_mat_part.shape[0]*ofmap_op_mat_part.shape[1]==0:
                        continue

                self.m_dim = ifmap_op_mat_part.shape[0]
                self.n_dim = filter_op_mat_part.shape[1]
                self.k_dim = filter_op_mat_part.shape[0]

                #print('ifmap: {}'.format(ifmap_op_mat_part.shape))
                #print('filter: {}'.format(filter_op_mat_part.shape))

                # Get PE util
                Util_this_pod = Get_Util(SA_row, SA_col, ifmap_op_mat_part.shape[0], filter_op_mat_part.shape[1])
                assert Util_this_pod <= 1.0, "PE util in this pod is bigger than 1.0"
                PE_util_this_layer.append(Util_this_pod)
                #

                compute_system = systolic_compute_os()
                if self.dataflow == 'ws':
                    compute_system = systolic_compute_ws()
                elif self.dataflow == 'is':
                    compute_system = systolic_compute_is() 
                compute_system.set_params(config_obj=self.single_arr_cfg,
                                        ifmap_op_mat=ifmap_op_mat_part,
                                        filter_op_mat=filter_op_mat_part,
                                        ofmap_op_mat=ofmap_op_mat_part)

                ifmap_prefetch_mat, filter_prefetch_mat = compute_system.get_prefetch_matrices()
                #print('ifmap_prefetch_mat: {}'.format(ifmap_prefetch_mat.shape))

                ifmap_demand_mat, filter_demand_mat, ofmap_demand_mat = compute_system.get_demand_matrices()
                #print('*ifmap_part: {}'.format(ifmap_op_mat_part.shape))
                #print('ifmap_part[-1]: {}'.format(ifmap_op_mat_part[-1]))
                #print('*ifmap shape: {}'.format(ifmap_demand_mat.shape)) ######
                #print(np.max(ifmap_demand_mat))
                #print('*filter shape: {}'.format(filter_demand_mat.shape))
                #print('*ofmap shape: {}'.format(ofmap_demand_mat.shape))

                memory_system = mem_dbsp()

                # Note: We use bytes, not kb.
                ifmap_buf_size_kb, filter_buf_size_kb, ofmap_buf_size_kb = self.single_arr_cfg.get_mem_sizes()
                ifmap_buf_size_bytes = ifmap_buf_size_kb
                filter_buf_size_bytes = filter_buf_size_kb
                ofmap_buf_size_bytes = ofmap_buf_size_kb

                arr_row, arr_col = self.single_arr_cfg.get_array_dims()

                ifmap_backing_bw = 1
                filter_backing_bw = 1
                ofmap_backing_bw = 1


                ###################################
                estimate_bandwidth_mode = False
                if self.single_arr_cfg.use_user_dram_bandwidth():
                    # bws = self.single_arr_cfg.get_bandwidths_as_list()
                    # print('BWs: {}'.format(bws))
                    # ifmap_backing_bw = bws[0]
                    # filter_backing_bw = bws[0]
                    # ofmap_backing_bw = bws[0]
                    arr_row, arr_col = self.single_arr_cfg.get_array_dims()

                    # The number 10 elems per cycle is arbitrary
                    if self.dataflow == 'os' or self.dataflow == 'ws':
                        ifmap_backing_bw = arr_row
                        filter_backing_bw = arr_col
                        ofmap_backing_bw = arr_col

                    elif self.dataflow == 'is':
                        ifmap_backing_bw = arr_col
                        filter_backing_bw = arr_row
                        ofmap_backing_bw = arr_col

                # CALC mode
                else:
                    dataflow = self.single_arr_cfg.get_dataflow()
                    arr_row, arr_col = self.single_arr_cfg.get_array_dims()
                    estimate_bandwidth_mode = True

                    # The number 10 elems per cycle is arbitrary
                    if self.dataflow == 'os' or self.dataflow == 'ws':
                        ifmap_backing_bw = 10
                        filter_backing_bw = 10
                        ofmap_backing_bw = 10

                    elif self.dataflow == 'is':
                        ifmap_backing_bw = arr_col
                        filter_backing_bw = arr_row
                        ofmap_backing_bw = arr_col
                #

                memory_system.set_params(
                    word_size=1,
                    ifmap_buf_size_bytes=ifmap_buf_size_bytes,
                    filter_buf_size_bytes=filter_buf_size_bytes,
                    ofmap_buf_size_bytes=ofmap_buf_size_bytes,
                    rd_buf_active_frac=0.5, wr_buf_active_frac=0.5,
                    ifmap_backing_buf_bw=ifmap_backing_bw,
                    filter_backing_buf_bw=filter_backing_bw,
                    ofmap_backing_buf_bw=ofmap_backing_bw,
                    verbose=False,
                    estimate_bandwidth_mode=estimate_bandwidth_mode,
                    get_input_dram=self.get_input_dram,
                    get_weight_dram=self.get_weight_dram
                )

                
                ###################################
                if self.single_arr_cfg.use_user_dram_bandwidth() :
                    memory_system.set_read_buf_prefetch_matrices(ifmap_prefetch_mat=ifmap_prefetch_mat,
                                                                    filter_prefetch_mat=filter_prefetch_mat)
                #####################################

                #
                if self.get_input_dram or self.get_weight_dram:
                    memory_system.service_memory_requests(ifmap_demand_mat, filter_demand_mat, ofmap_demand_mat)

                ##############################################################
                #######################Print Trace File#######################
                ##############################################################                                
                # # Write the traces
                # top_path = '../output_files/scalesim_results/palm_ff2_bwd/trace'
                # simname= 'palm_ff2_bwd' #실험명
                # dir_name = os.path.join(top_path, simname, 'layer' + str(layer_id), 'pod' + str(grid_col_id))
                # # Ensure all parent directories exist
                # os.makedirs(dir_name, exist_ok=True)

                # ifmap_sram_filename = dir_name +  '/IFMAP_SRAM_TRACE.csv'
                # filter_sram_filename = dir_name + '/FILTER_SRAM_TRACE.csv'
                # ofmap_sram_filename = dir_name +  '/OFMAP_SRAM_TRACE.csv'

                # ifmap_dram_filename = dir_name +  '/IFMAP_DRAM_TRACE.csv'
                # filter_dram_filename = dir_name + '/FILTER_DRAM_TRACE.csv'
                # ofmap_dram_filename = dir_name +  '/OFMAP_DRAM_TRACE.csv'

                # memory_system.print_ifmap_sram_trace(ifmap_sram_filename)
                # memory_system.print_ifmap_dram_trace(ifmap_dram_filename)
                # memory_system.print_filter_sram_trace(filter_sram_filename)
                # memory_system.print_filter_dram_trace(filter_dram_filename)
                # memory_system.print_ofmap_sram_trace(ofmap_sram_filename)
                # memory_system.print_ofmap_dram_trace(ofmap_dram_filename)
                #####################################               

                idram = memory_system.get_ifmap_dram_details()
                #print('IFMAP DRAM read in this grid: {}'.format(idram[2]))
                fildram = memory_system.get_filter_dram_details()
                #print('filter DRAM read in this grid: {}'.format(fildram[2]))
                self.ofdram = memory_system.get_ofmap_dram_details()

                ##############################################################
                #######################Print Trace File#######################
                ##############################################################

                # # Debug: ofmap dram writes for WS dataflow.
                # # Bug: Ofmap dram writes is multiplied by the number of folds.
                # if self.dataflow=='ws':
                #     IF_folds=np.ceil(ifmap_op_mat_part.shape[1]/SA_row)
                #     #Fil_folds=np.ceil(filter_op_mat_part.shape[1]/SA_col)
                #     num_folds=IF_folds
                #     self.ofdram=np.ceil(self.ofdram[2]/num_folds)
                #     #
                #     #print('OFMAP DRAM writes in this grid: {}'.format(self.ofdram))
                #     #print('DRAMs= {}, {}, {}'.format(idram[2],fildram[2],ofdram[2]))

                self.gather_stats(row_id=grid_row_id,
                                  col_id=grid_col_id,
                                  memory_system_obj=memory_system,
                                  compute_system_obj=compute_system,
                                  layer_id=layer_id)

        assert len(PE_util_this_layer)==(Used_row * Used_col), "util is not computed correctly."
        PE_util_this_layer = np.average(PE_util_this_layer) # PE util within "used pods"
        assert PE_util_this_layer <= 1.0, "PE util is bigger than 1.0"
        Entire_util_this_layer = pod_util_this_layer * PE_util_this_layer # PE util across "all pods"
        # print("UTIL DEBUG: {} {} {}".format(pod_util_this_layer, PE_util_this_layer, Entire_util_this_layer))
        assert Entire_util_this_layer <= 1.0, "util is bigger than 1.0"

        self.OVER_util.append(Entire_util_this_layer)

        self.all_grids_done = True

    #
    def run_simulations_all_layers(self):
        assert self.params_valid, 'Params are not valid'

        for lid in range(self.topo_obj.get_num_layers()):
            print('Running layer=' + str(lid))
            self.run_simulation_single_layer(lid) 

    #
    def get_opmat_parts(self, ifmap_op_mat, filter_op_mat, ofmap_op_mat,
                        grid_row_id, grid_col_id):

        ifmap_op_mat_part = np.zeros((1,1))
        filter_op_mat_part = np.zeros((1,1))
        ofmap_op_mat_part = np.zeros((1,1))
        if self.dataflow == 'os':
            ifmap_rows_per_part = math.ceil(ifmap_op_mat.shape[0] / self.grid_rows)
            ifmap_row_start_id = grid_row_id * ifmap_rows_per_part
            ifmap_row_end_id = min(ifmap_row_start_id + ifmap_rows_per_part, ifmap_op_mat.shape[0])
            ifmap_op_mat_part = ifmap_op_mat[ifmap_row_start_id:ifmap_row_end_id, :]

            filter_cols_per_part = math.ceil(filter_op_mat.shape[1] / self.grid_cols)
            filter_col_start_id = grid_col_id * filter_cols_per_part
            filter_col_end_id = min(filter_col_start_id + filter_cols_per_part, filter_op_mat.shape[1])
            filter_op_mat_part = filter_op_mat[:, filter_col_start_id:filter_col_end_id]

            ofmap_rows_per_part = math.ceil(ofmap_op_mat.shape[0]/ self.grid_rows)
            ofmap_row_start_id = grid_row_id * ofmap_rows_per_part
            ofmap_row_end_id = min(ofmap_row_start_id + ofmap_rows_per_part, ofmap_op_mat.shape[0])

            ofmap_cols_per_part = math.ceil(ofmap_op_mat.shape[1] / self.grid_cols)
            ofmap_col_start_id = grid_col_id * ofmap_cols_per_part
            ofmap_col_end_id = min(ofmap_col_start_id + ofmap_cols_per_part, ofmap_op_mat.shape[1])
            ofmap_op_mat_part = ofmap_op_mat[ofmap_row_start_id: ofmap_row_end_id,
                                             ofmap_col_start_id: ofmap_col_end_id]

        # DEBUG: transpose the weight opmat for WS & IS dataflows.
        elif self.dataflow == 'ws':
            #print(filter_op_mat)
            ifmap_rows_per_part = math.ceil(ifmap_op_mat.shape[0] / self.grid_rows)
            ifmap_row_start_id = grid_row_id * ifmap_rows_per_part
            ifmap_row_end_id = min(ifmap_row_start_id + ifmap_rows_per_part, ifmap_op_mat.shape[0])
            ifmap_op_mat_part = ifmap_op_mat[ifmap_row_start_id:ifmap_row_end_id, :]

            filter_cols_per_part = math.ceil(filter_op_mat.shape[1] / self.grid_cols)
            filter_col_start_id = grid_col_id * filter_cols_per_part
            filter_col_end_id = min(filter_col_start_id + filter_cols_per_part, filter_op_mat.shape[1])
            filter_op_mat_part = filter_op_mat[:, filter_col_start_id:filter_col_end_id]

            ofmap_rows_per_part = math.ceil(ofmap_op_mat.shape[0]/ self.grid_rows)
            ofmap_row_start_id = grid_row_id * ofmap_rows_per_part
            ofmap_row_end_id = min(ofmap_row_start_id + ofmap_rows_per_part, ofmap_op_mat.shape[0])

            ofmap_cols_per_part = math.ceil(ofmap_op_mat.shape[1] / self.grid_cols)
            ofmap_col_start_id = grid_col_id * ofmap_cols_per_part
            ofmap_col_end_id = min(ofmap_col_start_id + ofmap_cols_per_part, ofmap_op_mat.shape[1])
            ofmap_op_mat_part = ofmap_op_mat[ofmap_row_start_id: ofmap_row_end_id,
                                             ofmap_col_start_id: ofmap_col_end_id]

        elif self.dataflow == 'is':
            ifmap_rows_per_part = math.ceil(ifmap_op_mat.shape[0] / self.grid_rows)
            ifmap_row_start_id = grid_row_id * ifmap_rows_per_part
            ifmap_row_end_id = min(ifmap_row_start_id + ifmap_rows_per_part, ifmap_op_mat.shape[0])

            ifmap_cols_per_part = math.ceil(ifmap_op_mat.shape[1] / self.grid_cols)
            ifmap_col_start_id = grid_col_id * ifmap_cols_per_part
            ifmap_col_end_id = min(ifmap_col_start_id + ifmap_cols_per_part, ifmap_op_mat.shape[1])
            ifmap_op_mat_part = ifmap_op_mat[ifmap_row_start_id:ifmap_row_end_id,
                                             ifmap_col_start_id:ifmap_col_end_id]

            filter_rows_per_part = math.ceil(filter_op_mat.shape[0] / self.grid_cols)
            filter_row_start_id = grid_col_id * filter_rows_per_part
            filter_row_end_id = min(filter_row_start_id + filter_rows_per_part, filter_op_mat.shape[0])

            filter_op_mat_part = filter_op_mat[filter_row_start_id:filter_row_end_id,:]

            ofmap_rows_per_part = math.ceil(ofmap_op_mat.shape[0] / self.grid_rows)
            ofmap_row_start_id = grid_row_id * ofmap_rows_per_part
            ofmap_row_end_id = min(ofmap_row_start_id + ofmap_rows_per_part, ofmap_op_mat.shape[0])

            ofmap_op_mat_part = ofmap_op_mat[ofmap_row_start_id: ofmap_row_end_id, :]

        return ifmap_op_mat_part, filter_op_mat_part, ofmap_op_mat_part

    #
    def gather_stats(self, memory_system_obj, compute_system_obj,row_id, col_id, layer_id):
        # Stats to gather
        indx = row_id * self.grid_cols + col_id

        # 1. Compute cycles
        
        # Runtime re-calculation with analytical model
        SA_row, SA_col = self.single_arr_cfg.get_array_dims()
        this_m=self.m_dim
        this_k=self.k_dim
        this_n=self.n_dim

        fold_rt = (2*SA_row + SA_col + this_m - 1) # If you want to assume the weight double-buffering within the SA, modify "2*SA_row" to "SA_row".
        num_fold = np.ceil(this_k/SA_row) * np.ceil(this_n/SA_col)
        this_rt = fold_rt * num_fold
        self.stats_compute_cycles[layer_id, indx] = this_rt
        #

        # 2. Bandwidth requirements
        if self.get_input_dram:
            ifmap_start_cycle, ifmap_end_cycle, ifmap_dram_reads = memory_system_obj.get_ifmap_dram_details()
            self.input_dram_list.append(ifmap_dram_reads)
        if self.get_weight_dram:
            filter_start_cycle, filter_end_cycle, filter_dram_reads = memory_system_obj.get_filter_dram_details()
            self.weight_dram_list.append(filter_dram_reads)

        # SRAM R/W
        ifmap_sram_reads = compute_system_obj.get_ifmap_requests()
        filter_sram_reads = compute_system_obj.get_filter_requests()
        ofmap_sram_writes = compute_system_obj.get_ofmap_requests()

        self.stats_ifmap_sram_reads[layer_id, indx] = ifmap_sram_reads
        self.stats_filter_sram_reads[layer_id, indx] = filter_sram_reads
        self.stats_ofmap_sram_writes[layer_id, indx] = ofmap_sram_writes
        #

        self.stats_ifmap_dram_reads[layer_id, indx] = self.input_dram_list[row_id]
        self.stats_filter_dram_reads[layer_id, indx] = self.weight_dram_list[col_id]
        # self.stats_ofmap_dram_writes[layer_id, indx] = ofmap_dram_writes

        # self.stats_ifmap_dram_start_cycl[layer_id, indx] = ifmap_start_cycle
        # self.stats_filter_dram_start_cycl[layer_id, indx] = filter_start_cycle
        # self.stats_ofmap_dram_start_cycl[layer_id, indx] = ofmap_start_cycle

        # self.stats_ifmap_dram_end_cycl[layer_id, indx] = ifmap_end_cycle
        # self.stats_filter_dram_end_cycl[layer_id, indx] = filter_end_cycle
        # self.stats_ofmap_dram_end_cycl[layer_id, indx] = ofmap_end_cycle

    #
    def calc_overall_stats_all_layer(self):
        assert self.all_grids_done, 'Not all data is available'

        num_layers = self.topo_obj.get_num_layers()
        for layer_id in range(num_layers):
            # 1. Compute cycles
            this_layer_compute_cycles = max(self.stats_compute_cycles[layer_id])
            self.overall_compute_cycles_per_layers += [this_layer_compute_cycles]

            # 2. Overall utilization
            num_compute = self.topo_obj.get_layer_num_ofmap_px(layer_id=layer_id) \
                          * self.topo_obj.get_layer_window_size(layer_id=layer_id)

            row, col = self.single_arr_cfg.get_array_dims()
            total_compute_possible = self.grid_cols * self.grid_rows * row * col * this_layer_compute_cycles
            # this_layer_overall_util_perc = num_compute / total_compute_possible * 100
            this_layer_overall_util_perc = num_compute*self.batch_sz / total_compute_possible * 100

            self.overall_util_perc_per_layer += [this_layer_overall_util_perc]

            # 3. Memory stats
            self.total_ifmap_dram_reads += [sum(self.stats_ifmap_dram_reads[layer_id])]
            self.total_filter_dram_reads += [sum(self.stats_filter_dram_reads[layer_id])]
            self.total_ofmap_dram_writes += [sum(self.stats_ofmap_dram_writes[layer_id])]

            ################## SRAM
            self.total_ifmap_sram_reads += [sum(self.stats_ifmap_sram_reads[layer_id])]
            self.total_filter_sram_reads += [sum(self.stats_filter_sram_reads[layer_id])]
            self.total_ofmap_sram_writes += [sum(self.stats_ofmap_sram_writes[layer_id])]
            #################################################

        self.overall_compute_cycles_all_layers = sum(self.overall_compute_cycles_per_layers)
        self.overall_util_perc_all_layer = sum(self.overall_util_perc_per_layer) / num_layers
        ### Weighted Compute Util
        self.overall_util_perc_all_layer = Get_weighted_util(self.overall_compute_cycles_per_layers, self.overall_util_perc_per_layer)
        self.overall_util_perc_all_layer=np.round(self.overall_util_perc_all_layer,2)

        self.metrics_ready = True

    #
    def get_report_items(self):
        return self.overall_compute_cycles_all_layers, self.overall_util_perc_all_layer, \
               self.total_ifmap_dram_reads, self.total_filter_dram_reads, self.total_ofmap_dram_writes, \
               self.total_ifmap_sram_reads, self.total_filter_sram_reads, self.total_ofmap_sram_writes,self.overall_compute_cycles_per_layers, \
               self.OVER_util, self.POD_util
               #
    
    def get_report_items_per_pod(self):
        return self.stats_ifmap_dram_reads, self.stats_filter_dram_reads, self.stats_ofmap_dram_writes, self.topo_obj.get_num_layers()

def Get_Util(SA_row, SA_col, SR, SC):
    # Num folds
    FR=int(np.ceil(SR/SA_row))
    FC=int(np.ceil(SC/SA_col))
    
    Util_row = np.zeros(FR)
    for i in range(FR):
        if (i == (FR-1)) & ((SR % SA_row) != 0):
            Util_row[i] = SR % SA_row
        else:
            Util_row[i] = SA_row
    
    Util_col = np.zeros(FC)
    for i in range(FC):
        if (i == (FC-1)) & ((SC % SA_col) != 0):
            Util_col[i] = SC % SA_col
        else:
            Util_col[i] = SA_col

    Utilization = np.zeros([FR, FC])
    for i in range(FR):
        for j in range(FC):
            Utilization[i][j] = (Util_row[i] * Util_col[j]) / (SA_row * SA_col)
    Utilization = np.average(Utilization)

    return Utilization

def Get_weighted_util(cycles_per_layer, util_per_layer):
    Wutil=[]
    for i in range(len(cycles_per_layer)):
        CxU = (cycles_per_layer[i]/np.sum(cycles_per_layer)) * util_per_layer[i] # To get weighted utilization
        Wutil.append(CxU)
    Wutil = np.sum(Wutil)

    return Wutil

def Get_OFMAP_offchip_writes(toponame, batch):
    if ('BERT_mnk' in toponame) or ('GPT_mnk' in toponame) or ('TF_mnk' in toponame):
        mnk_flag = True 
    else:
        mnk_flag = False 

    if mnk_flag:
        topofile = '../input_files/topologies/pathways/palm/'+toponame+'.csv'
    else:
        topofile = '../input_files/topologies/pathways/palm/'+toponame+'.csv' 
    
    csvtopo=open(topofile,'r',encoding='cp949')

    ofparam=[]

    toporow=csv.reader(csvtopo)
    next(toporow)
    if mnk_flag:
        for topo in toporow:
            m=int(topo[1]) #num_of
            n=int(topo[2]) #num_fil
            k=int(topo[3]) # 여기가 중복 dim

            ofparam_this_layer = m*n
            ofparam.append(ofparam_this_layer)
    else:
        for topo in toporow:
            I_row=int(topo[1])
            I_col=int(topo[2])
            F_row=int(topo[3])
            F_col=int(topo[4])
            S=int(topo[7])
            Chan=int(topo[5])
            numFil=int(topo[6])

            ofparam_this_layer = np.ceil( (I_row-F_row+S)/S ) * np.ceil( (I_col-F_col+S)/S )
            ofparam_this_layer = ofparam_this_layer * numFil * batch
            ofparam.append(ofparam_this_layer)
    
    # ofparam_total = sum(ofparam)
    return ofparam

#



#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('topo', help='Set topology file')
    parser.add_argument('SAdim', help='Set SA dimension')
    parser.add_argument('PODdim', help='Set Pod dimension')
    parser.add_argument('batch', help='Set batch size')
    args = parser.parse_args()
    
    toponame= args.topo # Topology name (e.g.,alexnet)
    SAdim=args.SAdim
    SArow, SAcol = map(str, SAdim.split('x'))
    PODdim=args.PODdim
    batch_sz = int(args.batch)
    
    ##################################
    # Configurations                 #
    ##################################
    dflow = 'ws' # The simulator only supports WS dataflow.
    config_base = '../input_files/scalesim_configs/' # Config file folder
    Results_dir = '../output_files'
    input_SRAM = 4*1024*1024 # Total input VMEM of an accelerator, unit=Bytes
    weight_SRAM = 1*1024*1024 # Total weight VMEM of an accelerator, unit=Bytes
    # input_SRAM + 4*weight_SRAM = 16 MB
    # input_SRAM = 4*weight_SRAM = 8 MB
    # We use bfloat16 (2 bytes) in this simulation.
    # Instead of reflecting the data size, reduce the memory capacity by half.
    output_SRAM = 1*1024*1024 # Total output VMEM of an accelerator, unit=Bytes
    ##################################

    # DNN model related (Set mnk_flag and topology file)
    if ('BERT_mnk' in toponame) or ('GPT_mnk' in toponame) or ('TF_mnk' in toponame):
        mnk_flag = True 
    else:
        mnk_flag = False 

    if mnk_flag:
        topofile = '../input_files/topologies/pathways/palm/'+toponame+'.csv' 
    else:
        topofile = '../input_files/topologies/pathways/palm/'+toponame+'.csv' 

    # Make Config file
    cfgfname, cfgname = mkcfg(config_base, dflow, SArow, SAcol, input_SRAM, weight_SRAM, output_SRAM)
    
    grid_arr_dict = {PODdim:cfgfname,}
    x_labels = list(grid_arr_dict.keys())
    createDirectory(Results_dir)

    for gds in x_labels:
        DRAMS=[]
        SRAMS=[]
        RT=[]
        
        time_start=datetime.now()
        print(time_start)

        print('Running {}...'.format(gds))
        g_row, g_col = map(int, gds.split('x'))

        repname = SArow+'x'+SAcol+'SA_'+ str(g_row)+'x'+str(g_col)+'Pod_'+'batch'+str(batch_sz)
        repdir = '../output_files/scalesim_results/palm_ff2_bwd/Scaleout_Detail/'+toponame #./reports_detail/simname_toponame
        createDirectory('../output_files/scalesim_results/palm_ff2_bwd/Scaleout_Detail')
        createDirectory(repdir)
        rep = open(repdir + '/' + repname + '.txt','w') #./reports/toponame/Detail/repname.txt

        # arrsize = grid_arr_dict[gds]
        config_file = cfgname
        grid1 = scaled_out_simulator()
        grid1.set_params(topology_filename=topofile,
                        single_arr_config_file=config_file,
                        grid_rows=g_row, grid_cols=g_col, dataflow=dflow, mnk_input=mnk_flag, batch_size=batch_sz)

        grid1.run_simulations_all_layers()
        grid1.calc_overall_stats_all_layer()

        time_end = datetime.now()
        # print(time_end - time_start)

        # Get results
        cycles, util, ifmap_read, filter_reads, ofmap_writes, ifmap_read_sram, filter_reads_sram, ofmap_writes_sram, cycles_per_layer, util_all_layer, pod_util_per_layer = grid1.get_report_items()
        ofmap_writes = Get_OFMAP_offchip_writes(toponame, batch_sz) # overwrite with analytical value

        # Cycles are wrong if Batch size is not 1. Compute cycles and util using analytical model of SCALE-Sim.
        Wutil = np.round(Get_weighted_util(cycles_per_layer, util_all_layer)*100, 2)
        pod_Wutil = np.round(Get_weighted_util(cycles_per_layer, pod_util_per_layer)*100, 2)
        util_all_layer=np.round(np.average(np.array(util_all_layer))*100,2)

        overall_read=ifmap_read+filter_reads+ofmap_writes
        overall_read_sram=ifmap_read_sram+filter_reads_sram+ofmap_writes_sram

        all_cycles = [cycles]
        all_utils = [util]
        dram_arr = [[sum(ifmap_read), sum(filter_reads), sum(ofmap_writes)]] # Total DRAM access (for all layers)
        sram_arr = [[sum(ifmap_read_sram), sum(filter_reads_sram), sum(ofmap_writes_sram)]] # Total SRAM access (for all layers)
        ov_dram = [overall_read]
        ov_sram = [overall_read_sram]

        DRAMS.append(sum(ifmap_read)+sum(filter_reads)+sum(ofmap_writes))
        SRAMS.append(sum(ifmap_read_sram)+sum(filter_reads_sram)+sum(ofmap_writes_sram))
        RT.append(cycles)

        rep.write('\n***{} REPORT\n*Runtime= {}\n*DRAM reads= {}, {}, {}\n*total DRAM reads= {}\n'
            .format(gds, cycles, sum(ifmap_read), sum(filter_reads), sum(ofmap_writes), sum(ifmap_read)+sum(filter_reads)+sum(ofmap_writes)))
        rep.write('*SRAM reads= {}, {}, {}\n*total SRAM reads= {}\n'
            .format(sum(ifmap_read_sram), sum(filter_reads_sram), sum(ofmap_writes_sram), sum(ifmap_read_sram)+sum(filter_reads_sram)+sum(ofmap_writes_sram)))
        rep.write('*Weighted Util:{}\n'.format(Wutil))
        rep.write('*Weighted Pod Util:{}\n'.format(pod_Wutil))
        rep.write('*Per-layer info:\nRuntimes={}\nIFMAP_DRAM={}\nFilter_DRAM={}\nOFMAP_DRAM={}\n'.format(cycles_per_layer, ifmap_read, filter_reads, ofmap_writes))
        rep.write('IFMAP_SRAM={}\nFilter_SRAM={}\nOFMAP_SRAM={}\n'.format(ifmap_read_sram, filter_reads_sram, ofmap_writes_sram))
        rep.write('\nRT={}'.format(RT))
        rep.write('\nDRAMS={}'.format(DRAMS))
        rep.write('\nSRAMS={}\n'.format(SRAMS))
        rep.write('Batch Size:{}\n'.format(batch_sz))
        rep.write('\nElapsed Time={}\n'.format(str(time_end - time_start)))
        rep.close()

        repdir2='../output_files/scalesim_results/palm_ff2_bwd/Scaleout_Compact/'+toponame #./reports_compact/simname_toponame
        createDirectory('../output_files/scalesim_results/palm_ff2_bwd/Scaleout_Compact')
        createDirectory(repdir2)
        rep2 = open(repdir2 + '/' + repname + '.txt','w') #./reports/toponame/Detail/repname.txt

        rep2.write('Overall runtime cycles:{}\n'.format(sum(all_cycles))) #실행시간(사이클)
        rep2.write('Overall DRAM access:{}\n'.format(sum(ov_dram[0]))) #총 DRAM read
        rep2.write('Overall SRAM access:{}\n'.format(sum(ov_sram[0]))) #총 DRAM read
        rep2.write('Average PE Utilization:{}\n'.format(util_all_layer)) #Util 평균
        rep2.write('Compute Util:{}\n'.format(np.round(util,2)))
        rep2.write('DRAM reads:{}\n'.format(sum(ifmap_read)+sum(filter_reads)))
        rep2.write('DRAM writes:{}\n'.format(sum(ofmap_writes)))
        rep2.write('SRAM reads:{}\n'.format(sum(ifmap_read_sram)+sum(filter_reads_sram)))
        rep2.write('SRAM writes:{}\n'.format(sum(ofmap_writes_sram)))
        rep2.write('Weighted Util:{}\n'.format(Wutil))
        rep2.write('Weighted Pod Util:{}\n'.format(pod_Wutil))
        rep2.write('Batch Size:{}\n'.format(batch_sz))
        rep2.write('\nElapsed Time={}\n'.format(str(time_end - time_start)))
        rep2.close()
        # print(repname)
        
        print('Overall runtime cycles:{}'.format(sum(all_cycles))) 
        print('Overall DRAM access:{}'.format(sum(ov_dram[0]))) 
        print('Overall SRAM access:{}'.format(sum(ov_sram[0])))

        #per-pod
        ifmap_dram_pod, filter_dram_pod, ofmap_dram_pod, number_layers = grid1.get_report_items_per_pod()
        repdir3='../output_files/scalesim_results/palm_ff2_bwd/Scaleout_perPod/'+toponame #./reports_compact/simname_toponame
        createDirectory('../output_files/scalesim_results/palm_ff2_bwd/Scaleout_perPod')
        createDirectory(repdir3)
        rep3 = open(repdir3 + '/' + repname + '.txt','w') #./reports/toponame/Detail/repname.txt
        
        #stats_ifmap_dram_reads[layer_id, indx]
        rep3.write('per pod ifmap dram: ')
        for i in range(number_layers):
            rep3.write("{} ".format(ifmap_dram_pod[i]))
        rep3.write('\nper pod filter dram: ')
        for i in range(number_layers):
            rep3.write("{} ".format(filter_dram_pod[i]))
        rep3.write('\nper pod ofmap dram: ')
        for i in range(number_layers):
            rep3.write("{} ".format(ofmap_dram_pod[i]))
        rep3.close()