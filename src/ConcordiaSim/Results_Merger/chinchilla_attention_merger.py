#Modify file name, number in line 18, and number in line 25.
# Read the original CSV file, ignoring the first row
input_file = 'SDP_attention_timing.csv'
output_file = 'MH_attention_timing.csv'

with open(input_file, 'r') as file:
    lines = file.readlines()

# Extract header and data without removing the header
header = lines[0]
data_lines = lines[1:]

# Initialize the rows to be modified (starting with rows 1 to 10, which is index 0 to 9)
current_rows = data_lines[0:10]
all_modified_rows = []

# Repeat the copying and modification process 16 times
for _ in range(63):
    new_rows = []
    for line in current_rows:
        columns = line.strip().split(',')
        
        # Rule 3: Add 949548 to the first column, unless the value is -1
        if int(columns[0]) != -1:
            columns[0] = str(int(columns[0]) + 949548)
        
        # Rule 4: Add 949548 to the second column
        columns[1] = str(int(columns[1]) + 949548)
        
        # Rule 5: Add 0x000000010000 to the third column (preserve full hexadecimal representation)
        columns[2] = f"0x{int(columns[2], 16) + 0x000000010000:012x}"
        
        # Append the modified row to the new list
        new_rows.append(','.join(columns) + '\n')
    
    # Add the newly modified rows to the main list of all modified rows
    all_modified_rows.extend(new_rows)
    
    # Update current_rows for the next iteration
    current_rows = new_rows

# Add a newline before appending the modified rows
output_lines = [header] + data_lines + ['\n'] + all_modified_rows

# Write the resulting data to b.csv
with open(output_file, 'w') as file:
    file.writelines(output_lines)
