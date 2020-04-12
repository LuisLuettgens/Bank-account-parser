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
from pathlib import Path
from datetime import datetime, timedelta
import string

from pandas.plotting import register_matplotlib_converters

class DKB(base.BankAccount):
    def __init__(self, data_latest_file, pre_labeled=False, other_data_files = []):
        register_matplotlib_converters()
        print('')
        self.data_latest_file  = data_latest_file
        self.data_other_files  = other_data_files
        self.dfs               = []
        self.get_meta_info()
        self.load_keywords_from_db()
        self.pre_labeled = pre_labeled
        
        latest_data_file_compressed_path = self.erase_meta_data()
        
        self.DKB_header_unlabeled    = set(['Buchungstag', 'Wertstellung', 'Buchungstext', 'Auftraggeber / Begünstigter',   'Verwendungszweck', 'Kontonummer', 'BLZ', 'Betrag (EUR)', 'Gläubiger-ID', 'Mandatsreferenz', 'Kundenreferenz'])
    
        self.DKB_header_labeled      = self.DKB_header_unlabeled.copy()
        self.DKB_header_labeled.add('Balance')
        self.DKB_header_labeled.add('Transaction Label')
        
        self.DKB_header_labeled_list =['Buchungstag', 'Wertstellung', 'Buchungstext', 'Auftraggeber / Begünstigter', 'Verwendungszweck', 'Kontonummer', 'BLZ', 'Betrag (EUR)', 'Gläubiger-ID', 'Mandatsreferenz', 'Kundenreferenz', 'Balance', 'Transaction Label']
        
        
        col_types =  {'Betrag (EUR)':np.float,
                      'Balance': np.float}
        
        self.date_format='%d.%m.%Y'
        mydateparser = lambda x: pd.datetime.strptime(x, self.date_format)
        
        if self.pre_labeled:
            self.dfs.append(pd.read_csv(latest_data_file_compressed_path,
                                        delimiter=';',
                                        encoding ='latin-1',
                                        usecols=self.DKB_header_labeled,
                                        parse_dates=['Buchungstag', 'Wertstellung'],
                                        date_parser=mydateparser,
                                        dtype=col_types, decimal =',',
                                        thousands='.'))
        else:
            self.dfs.append(pd.read_csv(latest_data_file_compressed_path,
                                        delimiter=';',
                                        encoding ='latin-1',
                                        usecols=self.DKB_header_unlabeled,
                                        parse_dates=['Buchungstag', 'Wertstellung'],
                                        date_parser=mydateparser,
                                        dtype=col_types,decimal =',',
                                        thousands='.'))
         
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
        self.valid_table()
        #self.data = helper.add_balance_col(self.data, self.current_balance)
        
        self.daily_data = self.data[['Wertstellung','Betrag (EUR)']].groupby('Wertstellung', sort=False).sum().reset_index()
        self.daily_data = helper.add_balance_col(self.daily_data, self.current_balance)
        
        self.daily_data = self.update_daily()
        
        if not self.pre_labeled:
            self.label_rows()
        
        print('')
        self.info_labeled()
        
        self.start_date = min(self.data['Wertstellung'])
        self.end_date   = max(self.data['Wertstellung'])
        
        del self.data['index']
        
    
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
            
    def show_None(self,n=5):
        return self.data[self.data['Transaction Label'] == 'None'].sample(n=n)
    
    def prep_table(self): 
        print('Sorting the table based on Wertstellung-column...\t', end='')
        self.data = self.data.sort_values(by='Wertstellung', ascending=False)
        self.data = self.data.reset_index()
        print('done!')
        
        if not self.pre_labeled:
            print('Adding a transaction label column...\t\t\t', end='')
            self.data['Transaction Label'] = 'None'
            print('done!')
         
            print('Adding a column with the daily balance...\t\t', end='')
            self.data = helper.add_balance_col(self.data, self.current_balance)
            print('done!')
    
    def valid_table(self):
        print('Checking whether table is in expcted DKB-format...\t', end='')
        
        if self.pre_labeled:
            missing_cols = self.DKB_header_labeled.difference(self.data.columns)
        else:
            missing_cols = self.DKB_header_unlabeled.difference(self.data.columns)
        
        if(len(missing_cols) == 1):
            raise ValueError('The column: '  + ', '.join(missing_cols) + ' does not appear as a column name in the provided csv. Please make sure that it exists and try again...')

        if(len(missing_cols) > 1):
            raise ValueError('The columns: ' + ', '.join(missing_cols) + ' do not appear as a column names in the provided csv. Please make sure that it exists and try again...')
        
        print('done!')

        pd.set_option('display.max_columns', None)
        self.prep_table()
        
    def info_labeled(self):
        None_idx = self.data['Transaction Label'].value_counts().index.to_list().index('None')
        transaction_label_vals = self.data['Transaction Label'].value_counts().values[None_idx]
        
        if self.pre_labeled:
            print('In total',"{:.2f}".format((1-transaction_label_vals/self.data['Transaction Label'].shape[0])*100),"% of all transactions have been labeled.")
        else:
            print('In total',"{:.2f}".format((1-transaction_label_vals/self.data['Transaction Label'].shape[0])*100),"% of all transactions have labels.")
        
        print('')
        
    def get_categorie(self,categorie,start = None,end = None):
        if start == None:
            start = self.start_date
        
        if end == None:
            end = self.end_date
            
        if categorie not in self.categories:
            print('ERROR: This is an unknown categorie!\n')
            print('Choose one of the following categories:')
            for i, cat in enumerate(self.categories):
                print(i,': ', cat)
            return False
        else:
            df_trans = self.get_months(start,end,use_daily_table=False)
            return df_trans[df_trans['Transaction Label'] == categorie]
        
    def load_keywords_from_db(self, path='database.db'):
        extenstions = ['.bak', '.dat', '.dir']
        if all(list(map(lambda x: Path(path+x).is_file(),extenstions))):
            database        = shelve.open(path)
            self.db         = dict(database)
            self.categories = list(self.db.keys())
            self.categories.append('Rent')
            self.categories.append('None')
            self.categories.append('Private')
        else:
            print('Could not find a file under the given path:', path)
            raise ValueError('Could not find a file under the given path: ' + path)
            
    def all_categories(self):
        return self.categories
    
    def save_data(self,path):
        self.data.to_csv(path,sep=';',quoting=int(True), encoding ='latin-1', date_format=self.date_format, columns=self.DKB_header_labeled_list)
        
        with open(path, "r") as f:
            lines = f.readlines()
            
        with open(path, "w") as f:
            for line in self.meta_data_lines:
                f.write(line)
            for line in lines:
                f.write(line)
                
    def label_rows(self):
        print('Adding labels to transactions...\t\t\t', end='')
        self.load_keywords_from_db()
        for idx, row in self.data.iterrows():
            row_df = pd.DataFrame(row).T
            if row_df.loc[idx, 'Transaction Label'] != 'None':
                continue
            else:
                for key in (self.db).keys():
                    label = key
                    for cat_key in self.db[key].keys():
                        col_name = cat_key
                        if row_df[col_name].str.contains("|".join(self.db[key][cat_key]),case=False,na=False).values[0]:
                            self.data.loc[idx,'Transaction Label'] = label
            
                if helper.is_miete(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'Rent'
        print('done!')
 
     