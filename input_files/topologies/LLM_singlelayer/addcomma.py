import csv

# Specify the input and output file names
input_file = "T5_512_encoder_onelayer.csv"
output_file = "T5_512_encoder.csv"

# Open the input CSV file for reading and the output CSV file for writing
with open(input_file, "r", newline="") as in_csvfile, open(output_file, "w", newline="") as out_csvfile:
    reader = csv.reader(in_csvfile)
    writer = csv.writer(out_csvfile)

    for row in reader:
        # Append a comma to each row
        row.append("")
        writer.writerow(row)

print(f"Commas added to each row. Output written to {output_file}")
