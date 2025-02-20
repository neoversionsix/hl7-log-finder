import os
import datetime

# Input Variables
searchterm = 'THUY'
# Note: Dates must be in the format YYYYMMDD, also searching more than one day is very slow
date_greater_than = '20241205'
date_less_than = '2024120'

# Make dates numbers
date_greater_than = int(date_greater_than)
date_less_than = int(date_less_than)

# Create output filename
outputfilename = 'OUTPUT-'
datetime_str = str(datetime.datetime.now())
datetime_str = datetime_str.replace('.', '_')
datetime_str = datetime_str.replace(':', '-')
filetype = '.md'
outputfilename = outputfilename + datetime_str + filetype

# Initialize a list to store output lines
output_lines = ['# HL7 Search Results\n']

path = r'\\whsrhaparch1\RhapsodyHL7FileLogs_Prod\MasterLog'
os.chdir(path)
files = os.listdir()
folders = list(filter(lambda x: not x.endswith('zip'), files))

# Filter folders for date greater than this number
filtered_folders = [item for item in folders if date_greater_than < int(item[:8]) < date_less_than]

print('# HL7 Search Results')
for afolder in filtered_folders:
    path2 = os.path.join(path, afolder)
    files2 = os.listdir(path2)
    for afile in files2:
        filepath = os.path.join(path2, afile)
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f: 
            read_data = f.read()
            hl7_list = read_data.split('======')
            for hl7message in hl7_list:
                if searchterm in hl7message:
                    print('## ', filepath)
                    print(hl7message)
                    
                    # Append to output_lines instead of writing to file
                    output_lines.append(f'## {filepath}\n')
                    output_lines.append(f'{hl7message}\n')
                    print('Added HL7 message to output')

# Write all output to file at once
try:
    # Open the file using os.open
    fd = os.open(outputfilename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    
    # Write the content
    for line in output_lines:
        os.write(fd, line.encode('utf-8'))
    
    # Close the file
    os.close(fd)
    
    print(f"Successfully wrote output to {outputfilename}")
except Exception as e:
    print(f"Error writing to file: {e}")
    # If we still can't write to the file, print the contents to console
    print("Printing results to console instead:")
    print(''.join(output_lines))

print("done!")