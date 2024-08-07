# Input Variables
searchterm = '9999999'
date_greater_than = '20210609'
date_less_than = '202106010'

import os
import datetime

# Make dates numbers
date_greater_than=int(date_greater_than)
date_less_than = int(date_less_than)

# Create Output file (causes permission errors)

outputfilename = 'OUTPUT-'
datetime_str = str(datetime.datetime.now())
datetime_str = datetime_str.replace('.', '_')
datetime_str = datetime_str.replace(':', '-')
filetype = '.md'
outputfilename = outputfilename + datetime_str + filetype
outputfilename = str(outputfilename)
out_file = open(outputfilename, 'x')
out_file.writelines('# HL7 Search Results' + '\n')
out_file.close()


path = r'\\whsrhaparch1\RhapsodyHL7FileLogs_Prod\MasterLog'
os.chdir(path)
files = os.listdir()
folders = list(filter(lambda x: not x.endswith('zip'), files))

# Filter folders for date greater than this number
filtered_folders = []

for item in folders:
    folder_date = item[0:8]
    folder_date = int(folder_date)
    if ((folder_date > date_greater_than) and (folder_date < date_less_than)):
        filtered_folders.append(item)

string = '# HL7 Results'
print('# HL7 Search Results')
for afolder in filtered_folders:
    path2 = os.path.join(path, afolder)
    files2 = os.listdir(path2)
    for afile in files2:
        filepath = os.path.join(path2, afile)
        with open(filepath, 'r') as f:
            read_data = f.read()
            hl7_list = read_data.split('======')
            for hl7message in hl7_list:
                if searchterm in hl7message:
                    #print('## ', filepath)
                    #print(hl7message)              
                    # Below Has Permission Errors
                    
                    out_file = open(outputfilename, 'w')
                    out_file.writelines('##' + filepath + '\n')
                    out_file.writelines( hl7message + '\n')
                    print('wrote HL7 message to file')
                    out_file.close()
