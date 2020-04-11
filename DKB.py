# -*- coding: utf-8 -*-
"""
Created on Fri Apr 10 12:52:19 2020

@author: LUL3FE
"""

import BankAccount as base
import helper as helper 
import functools
import pandas as pd
import numpy as np
import os
import shelve
import re

from pandas.plotting import register_matplotlib_converters

class DKB(base.BankAccount):
    def __init__(self, data_latest_file, other_data_files = []):
        #register_matplotlib_converters()
        print('')
        self.data_latest_file  = data_latest_file
        self.data_other_files  = other_data_files
        self.dfs               = []
        print('Generating meta data...\t\t\t\t\t', end='')
        self.meta_data_lines   = ''
        self.meta_data         = helper.get_meta_info(self.data_latest_file)
        self.current_balance   = float(self.meta_data['Balance'].replace('.','').replace(',','.'))
        self.currency          = self.meta_data['Currency']
        self.bank_account_type = self.meta_data['BA_type']
        self.IBAN              = self.meta_data['IBAN']
        print('done!')
        self.categories       = ['Groceries', 'Dining', 'Amazon', 'Rent', 'Mobil phone /\n Internet', 'Culture',
                                 'Travel', 'Credit card',  'Fuel', 'Insurance', 'EoQ', 'Pharmacy', 'None']
        
        self.db               = self.load_keywords_from_db()
        latest_data_file_compressed_path = self.erase_meta_data()
        self.dfs.append(pd.read_csv(latest_data_file_compressed_path,delimiter=';', encoding ='latin-1'))
        os.remove(latest_data_file_compressed_path)
        
        for data_file in self.data_other_files:
            print('Parsing file: ' + data_file +'...\t\t\t', end='')
            if not helper.is_valid_csv_file(data_file):
                raise ValueError('The input file causes problems. Please input an other file...')
            else:
                self.dfs.append(pd.read_csv(helper.erase_meta_data(data_file),delimiter=';', encoding ='latin-1'))
                print('done!')
        
        append_ignore_idx = functools.partial(pd.DataFrame.append,ignore_index=True)
        
        self.data = functools.reduce(append_ignore_idx,self.dfs)
        self.data = helper.valid_table(self.data,self.current_balance)
        
        self.daily_data = self.data[['Wertstellung','Betrag (EUR)']].groupby('Wertstellung').sum().reset_index()
        self.daily_data = helper.add_balance_col(self.daily_data, self.current_balance)
        
        print('Updatig daily transactions...\t\t\t\t', end='')
        self.daily_data = self.update_daily()
        print('done!')
        
        print('Deleting unnamed columns...\t\t\t\t', end='')
        for elem in [col for col in self.data.columns if re.search('Unnamed 11',col)]:
            print(elem)
            self.data[elem].pop(None)
        print('done!')
        
        print('Adding labels to transactions...\t\t\t', end='')
        self.label_rows()
        print('done!')
        
        print('')
        self.info_labeled()
        
    
    def change_label_by_hand(self,row_idx,label):
        if label not in self.categories:
            print('This is not a valid label. Please choose one from the list below')
            for label in self.categories:
                print(label)
            print('')
            return False
        else:
            current_label = self.data.loc[row_idx,'Transaction Label']
            self.data.loc[row_idx,'Transaction Label'] = label
            counterpart = self.data.loc[row_idx,'Auftraggeber / Begünstigter']
            print('Changed the label from: ', current_label, 'to', label, '.')
            output = ' '.join(['Do you want to change all transactions with', counterpart, 'to', label, '?[y/n]\t'])
            user_input = input(output)
            if user_input == 'y':
                print('Changing all other labels accordingly...\t', end='')
                for idx in self.data[self.data['Auftraggeber / Begünstigter'].str.contains(counterpart,case=False,na=False)].index:
                    self.data.loc[idx,'Transaction Label'] = label
                print('done!')
                return self.data[self.data['Auftraggeber / Begünstigter'].str.contains(counterpart,case=False,na=False)]
            else:
                return pd.DataFrame(self.data.iloc[row_idx]).T