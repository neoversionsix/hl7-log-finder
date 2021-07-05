import os

path = r'\\whsrhaparch1\RhapsodyHL7FileLogs_Prod\MasterLog'
os.chdir(path)
files = os.listdir()
folders = list(filter(lambda x: not x.endswith('zip'), files))

searchterm = '999999999'

for afolder in folders:
    path2 = os.path.join(path, afolder)
    files2 = os.listdir(path2)
    for afile in files2:
        filepath = os.path.join(path2, afile)
        with open(filepath, 'r') as f:
            read_data = f.read()
            hl7_list = read_data.split('======')
            for hl7message in hl7_list:
                if searchterm in hl7message:
                    print(filepath)
                    print(hl7message)
                    print('')
