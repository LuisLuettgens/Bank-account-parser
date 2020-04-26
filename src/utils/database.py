import json
import helper
import BankAccounts
import pandas as pd
from datetime import datetime, timedelta

class Database():
    def __init__(self,path: str):
        print("Database constructor!")
        helper.is_valid_json_file(path)
        with open(path) as f:
            self.data = data = json.load(f)
        self.labels = list(self.data.keys())

"""
db = Database('../../database/keywords.json')

date_format = '%d.%m.%Y'
date_parser_dkb = lambda x: datetime.strptime(str(x), date_format)
df = pd.read_csv('/home/luis/Documents/1036976429_mini_sample.csv',
            delimiter=';',
            encoding='latin_1',
            decimal=',',
            thousands='.',
            engine='python',
            header=0,
            date_parser=date_parser_dkb)

def label_rows(df):
    counter = 0
    print('Adding labels to transactions...\t\t\t', end='')
    for idx, row in df.iterrows():
        counter+=1
        if counter == 14:
            break
        row_df = pd.DataFrame(row).T
        print(row_df)
        print()
        print('##################################################')
        for key in db.data.keys():
            label = key
            compose = db.data[label]['Compose']
            result_per_column = []
            for col_name in db.data[label]:
                if col_name == 'Compose' or db.data[label][col_name] is None:
                    continue
                
                #print('\t',col_name, ':', db.data[label][col_name])
                result_per_column.append(row_df[col_name].str.contains("|".join(db.data[label][col_name]),case=False,na=False).values[0])
            if len(result_per_column) == 0:
                continue
            print(label,':',result_per_column)
            print('Compose',compose)
            if compose == 'and':
                if all(result_per_column):
                    print('\tall matched') #self.data.loc[idx,'Transaction Label'] = label
            elif compose == 'or':
                if any(result_per_column):
                    print('\tany matched') #self.data.loc[idx,'Transaction Label'] = label
            elif compose is None:
                if any(result_per_column):
                    print('\tcompose is None value is True matched') #self.data.loc[idx,'Transaction Label'] = label
            print()

    print('done!')
    return True

label_rows(df)
"""
    