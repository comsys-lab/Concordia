import csv

def convert_csv_to_trace(csv_filename, trace_filename):
    with open(csv_filename, 'r') as csv_file, open(trace_filename, 'w') as trace_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)  # Skip the header row

        # Initial values for the first row in the trace file
        arrival_time = 0
        device_number = 0
        starting_logical_sector_address = 1

        for row in csv_reader:
            # Extract relevant fields from csv file
            computation_start_cycle, eviction_available_cycle, data_index, data_size = row
            data_size = int(data_size)

            # Calculate Request_Size_In_Sectors
            request_size_in_sectors = data_size // 512

            # Determine read/write value from data_index LSB
            lsb = int(data_index[-1], 16)  # Last character of data_index in hex
            read_write = 1 if lsb in [0, 1] else 0

            # Write the trace line to the file
            trace_line = f"{arrival_time} {device_number} {starting_logical_sector_address} {request_size_in_sectors} {read_write}\n"
            trace_file.write(trace_line)

            # Update values for the next row
            arrival_time += 100
            starting_logical_sector_address += request_size_in_sectors

def split_trace_file(input_trace_filename, write_trace_filename, read_trace_filename):
    with open(input_trace_filename, 'r') as input_trace_file, \
         open(write_trace_filename, 'w') as write_trace_file, \
         open(read_trace_filename, 'w') as read_trace_file:
        
        for line in input_trace_file:
            # Split the line into columns
            columns = line.strip().split()
            
            # Get the value of the 5th column (index 4)
            read_write_value = int(columns[4])
            
            # Write to the appropriate trace file based on the read/write value
            if read_write_value == 0:
                write_trace_file.write(line)
            elif read_write_value == 1:
                read_trace_file.write(line)

# Use the function to convert test.csv to mqsim_bert_trace.trace
convert_csv_to_trace('bert_large_24layers.csv', 'mqsim_bert_trace.trace')

# Split the generated trace file into read and write trace files
split_trace_file('mqsim_bert_trace.trace', 'mqsim_bert_write.trace', 'mqsim_bert_read.trace')
