import os
import glob
import pandas as pd

LINES = ["SS-1", "SS-2", "FZ", "EB"]

for line in LINES:
    base_dir = "/Users/cdobson/Documents/Datateam/biofouling_project/output/"+line+"_Gliders"
    os.chdir(base_dir)

    extension = 'csv'
    all_filenames = [i for i in glob.glob('*.{}'.format(extension))]
    all_filenames.sort()

    #combine all files in the list
    combined_csv = pd.concat([pd.read_csv(f) for f in all_filenames ])
    #export to csv
    csv_name = line+"_Gliders_Combined.csv"
    combined_csv.to_csv(csv_name, index=False, encoding='utf-8-sig')
