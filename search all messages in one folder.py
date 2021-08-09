'''
This script reads all the logs in a given folder
it then outputs all the hl7 messages to an excel
file if they have the searchterm in them'''


# Input Variables
searchterm = '99'
path = r'C:\hl7data'
output_filename = 'OUTPUT.xlsx'
output_file_path = path + r'\\' + output_filename

# Import Libs
import os
import pandas as pd

# Get a list of all the log files
hl7_log_files = os.listdir(path)

# Do work
matching_messages_list = []
for afile in hl7_log_files:
    filepath = os.path.join(path, afile)
    with open(filepath, 'r') as f:
        read_data = f.read()
        hl7_list = read_data.split('======')
        filtered_hl7_list = list(filter(lambda k: searchterm in k, hl7_list))
        matching_messages_list = [*matching_messages_list, *filtered_hl7_list]

# Output the data to an excel sheet            
df = pd.DataFrame({'messages':matching_messages_list})
df.to_excel(output_file_path, index=False)