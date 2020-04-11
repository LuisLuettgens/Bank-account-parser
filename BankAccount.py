# -*- coding: utf-8 -*-
"""
Created on Wed Apr  8 12:31:58 2020

@author: LUL3FE
"""
import numpy as np
import os
import re
import string
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from IPython.core.display import display, HTML
from pathlib import Path
import functools
from helper import *
from pandas.plotting import register_matplotlib_converters
import shelve

class BankAccount:
    def __init__(self, data_latest_file, other_data_files = []):
        register_matplotlib_converters()
        print('')
        self.data_latest_file  = data_latest_file
        self.data_other_files  = other_data_files
        self.dfs               = []
        print('Generating meta data...\t\t\t\t\t', end='')
        self.meta_data_lines   = ''
        self.meta_data         = self.get_meta_info(self.data_latest_file)
        self.current_balance   = float(self.meta_data['Balance'].replace('.','').replace(',','.'))
        self.currency          = self.meta_data['Currency']
        self.bank_account_type = self.meta_data['BA_type']
        self.IBAN              = self.meta_data['IBAN']
        print('done!')
        self.categories       = ['Groceries', 'Dining', 'Amazon', 'Rent', 'Mobil phone /\n Internet', 'Culture',
                                 'Travel', 'Credit card',  'Fuel', 'Insurance', 'EoQ', 'Pharmacy', 'None']
        
        latest_data_file_compressed_path = self.erase_meta_data()
        self.dfs.append(pd.read_csv(latest_data_file_compressed_path,delimiter=';', encoding ='latin-1'))
        os.remove(latest_data_file_compressed_path)
        
        for data_file in self.data_other_files:
            print('Parsing file: ' + data_file +'...\t\t\t', end='')
            if not is_valid_csv_file(data_file):
                raise ValueError('The input file causes problems. Please input an other file...')
            else:
                self.dfs.append(pd.read_csv(erase_meta_data(data_file),delimiter=';', encoding ='latin-1'))
                print('done!')
        
        append_ignore_idx = functools.partial(pd.DataFrame.append,ignore_index=True)
        self.data = functools.reduce(append_ignore_idx,self.dfs)
        self.data = valid_table(self.data,self.current_balance)
        self.daily_data = self.data[['Wertstellung','Betrag (EUR)']].groupby('Wertstellung').sum().reset_index()
        self.daily_data = add_balance_col(self.daily_data, self.current_balance)
        print('Updatig daily transactions...\t\t\t\t', end='')
        self.daily_data = self.update_daily()
        print('done!')
        print('Deleting unnamed column...\t\t\t\t', end='')
        del self.data['Unnamed: 11']
        print('done!')
        print('Adding labels to transactions...\t\t\t', end='')
        self.label_row()
        print('done!')
        print('')
        None_idx = self.data['Transaction Label'].value_counts().index.to_list().index('None')
        transaction_label_vals = self.data['Transaction Label'].value_counts().values[None_idx]       
        print('In total',
              "{:.2f}".format((1-transaction_label_vals/self.data['Transaction Label'].shape[0])*100),
              "% of all transactions have been labels.")
        print('')
        
    def get_data(self):
        return self.data
    
    def get_data_daily(self):
        return self.daily_data()
            
    def get_months(self, start_date, end_date, use_daily_table=True, use_Werstellung = True):
        if use_Werstellung:
            if use_daily_table:
                return self.daily_data[ (self.daily_data['Wertstellung'] >= start_date) &
                                        (self.daily_data['Wertstellung'] <  end_date)]
            else:
                return self.data[(self.data['Wertstellung'] >= start_date) &
                                (self.data['Wertstellung'] <  end_date)]
        else:
            if use_daily_table:
                return self.daily_data[(self.daily_data['Buchungstag'] >= start_date) &
                                       (self.daily_data['Buchungstag'] <  end_date)]
            else:
                return self.data[(self.data['Buchungstag'] >= start_date) &
                            (self.data['Buchungstag'] <  end_date)]
                
    def last_month(self):
        return self.get_months(n_months_back(1),datetime.now(),use_daily_table=False)
        
    def last_month_daily(self):
        return self.get_months(n_months_back(1),datetime.now())

    
    def last_quater(self,use_daily_table=True):
        return self.get_months(n_months_back(3),datetime.now(),use_daily_table)
    
    def summary(self,start,end):
        
        # preparation
        df       = self.get_months(start,end)
        df_trans = self.get_months(start,end,use_daily_table=False)
            
        # Account balance & transactions
        Wert   = df['Wertstellung']
        Bal    = df['Balance']
        Betrag = df['Betrag (EUR)']
        
        dates  = list(Wert[0:-1:int(np.floor(len(Wert)/6))])
        xlabels =[x.date().strftime('%Y-%m-%d') for x in dates]
        
        
        # Expenses per month plot
        expenses, total_expenses = self.cluster_expenses(*self.total_expenses(df_trans))
        
        # Compare expenses to previous time period
        diff = (end-start).days
        
        begin_prev_period = start - timedelta(days=diff+1)
        end_prev_period   = start - timedelta(days=1)

        pref_period_trans = self.get_months(begin_prev_period,end_prev_period,use_daily_table=False)
        diff = self.trend_adjacent(df_trans,pref_period_trans)
        
        # Income vs. Expenses
        total_salary = df_trans.loc[(df_trans['Betrag (EUR)'] > 0) & (df_trans['Transaction Label'] == 'Salary')].sum()['Betrag (EUR)']  
        other_income = df_trans.loc[(df_trans['Betrag (EUR)'] > 0) & (df_trans['Transaction Label'] != 'Salary')].sum()['Betrag (EUR)']  
        
        category_names = ['Salary', 'Other income', 'Expenses']
        results = {'': [total_salary, other_income, total_expenses]}

        data = np.array(list(results.values()))
        data_cum = data.cumsum(axis=1)
        category_colors = plt.get_cmap('Blues')(
        np.linspace(0.15, 0.85, data.shape[1]))
        
        # Create plots
        nrows = 3
        ncols = 2
        fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(ncols*10, nrows*10))
        
        # Accounts balance plot
        axes[0,0].plot(Wert,Bal)
        axes[0,0].set_xticklabels(xlabels, rotation=20)
        axes[0,0].set_title("Account Balance")
        
        # Account transaction
        axes[0,1].plot(Wert,Betrag)
        axes[0,1].set_xticklabels(xlabels, rotation=20)
        axes[0,1].set_title("Spendings")

        # Expenses per categorie
        axes[1,0].pie(expenses.values(),labels=expenses.keys(), autopct='%1.1f%%',shadow=True, startangle=90)
        axes[1,0].axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        axes[1,0].set_title("Expenses per category")
        
        # Compare with last period
        axes[1,1].bar(diff.keys(),diff.values())
        axes[1,1].axhline(y=0.0, color='k', linestyle='-')
        axes[1,1].set_xticklabels(diff.keys(), rotation=60)
        axes[1,1].set_title("Compare with last period")
    
        # Income versus expenses
        axes[2,0].invert_yaxis()
        axes[2,0].xaxis.set_visible(False)
        axes[2,0].set_xlim(0, np.sum(data, axis=1).max())
        
        for i, (colname, color) in enumerate(zip(category_names, category_colors)):
            widths = data[:, i]
            starts = data_cum[:, i] - widths
            axes[2,0].barh('', widths, left=starts, height=0.5,
                    label=colname, color=color)
            xcenters = starts + widths / 2
    
            r, g, b, _ = color
            text_color = 'white' if r * g * b < 0.5 else 'darkgrey'
            for y, (x, c) in enumerate(zip(xcenters, widths)):
                axes[2,0].text(x, y, str(int(c)) + '€', ha='center', va='center',
                        color=text_color, fontsize='xx-large')
                axes[2,0].legend(ncol=len(category_names), bbox_to_anchor=(0, 1), loc='lower left', fontsize='xx-large')
    
        # Set title
        title = "".join(['Summay for period: ', start.date().strftime('%Y-%m-%d'), ' - ',end.date().strftime('%Y-%m-%d')])
        fig.suptitle(title , fontsize=16)
    
    def summary_last_quater(self):
        now = datetime.now()
        last_year = now.year-1
        prev_Q4_start = datetime(last_year,10,1,0,0,0)
        Q1_start = datetime(now.year,1,1,0,0,0)
        Q2_start = datetime(now.year,4,1,0,0,0)
        Q3_start = datetime(now.year,7,1,0,0,0)
        Q4_start = datetime(now.year,10,1,0,0,0)
        
        prev_Q4_end = Q1_start - timedelta(days=1)
        Q1_end      = Q2_start - timedelta(days=1)
        Q2_end      = Q3_start - timedelta(days=1)
        Q3_end      = Q4_start - timedelta(days=1)
        
        quartals = [(prev_Q4_start,prev_Q4_end),
                              (Q1_start,Q1_end),
                              (Q2_start,Q2_end),
                              (Q3_start,Q3_end)]
        
        return self.summary(*quartals[int((now.month-1)/3)])
        
        
    def update_daily(self):
        daily_wertstellung = list(self.daily_data['Wertstellung'])
        start_date = min(daily_wertstellung)
        end_date   = max(daily_wertstellung)
        days = generate_days(start_date, end_date)
        df = pd.DataFrame({'Wertstellung': [], 'Betrag (EUR)': [], 'Balance': []})
    
        for day in days:
            s = pd.Series({'Wertstellung': day, 'Betrag (EUR)': 0, 'Balance': None})
            df = df.append(s,ignore_index=True)
               
        for index, row in self.daily_data.iterrows():
            WERT    = row['Wertstellung']
            BETRAG  = row['Betrag (EUR)']
            BALANCE = row['Balance']
            idx = df.index[df['Wertstellung'] == WERT]
            df.loc[idx,'Betrag (EUR)'] = BETRAG
            df.loc[idx,'Balance']      = BALANCE
                
        for idx, row in df.iterrows():
            if row['Balance'] == None:
                df.loc[idx,'Balance'] = df.loc[idx-1,'Balance']
        return df
    
    def label_rows(self):
        labels_dict = self.load_keywords_from_db()
        for idx, row in self.data.iterrows():
            row_df = pd.DataFrame(row).T
            for key in (self.db).keys():
                label = key
                for cat_key in self.db[key].keys():
                    col_name = cat_key
                    if row_df[col_name].str.contains("|".join(self.db[key][cat_key]),case=False,na=False).values[0]:
                        self.data.loc[idx,'Transaction Label'] = label
        
            if is_miete(row_df).values[0]:
                self.data.loc[idx,'Transaction Label'] = 'Rent'
      
    def total_expenses(self, df):
        total_expenses = -df.loc[df['Betrag (EUR)'] < 0].sum()['Betrag (EUR)']
        expenses = {}
        for categorie in self.categories:
            expenses[categorie] = -df.loc[(df['Betrag (EUR)'] < 0) & (df['Transaction Label'] == categorie)].sum()['Betrag (EUR)']
        return expenses, total_expenses
    
    def cluster_expenses(self,d,total_expenses, min_quota = 0.025):
        d['other'] = 0.
        for key in d.copy().keys():
            if d[key] < min_quota*total_expenses:
                d['other'] += d[key]
                del d[key]
        return d, total_expenses
    
    def categorie_expenses(self, df, categorie):
        return {categorie: -df.loc[(df['Betrag (EUR)'] < 0) & (df['Transaction Label'] == categorie)].sum()['Betrag (EUR)']}    
        
    def get_categorie(self,categorie,start,end):
        if categorie not in self.categories:
            print('ERROR: This is an unknown categorie!\n')
            print('Choose one of the following categories:')
            for i, cat in enumerate(self.categories):
                print(i,': ', cat)
            return False
        else:
            df_trans = self.get_months(start,end,use_daily_table=False)
            return df_trans[df_trans['Transaction Label'] == categorie]
    
    def trend_adjacent(self,df1, df2):
        # assuming they are actually adjacent
        df1_lastest = True
        if max(df1['Wertstellung']) < max(df2['Wertstellung']):
            df1_lastest = False
        
        df1_expenses, _ = self.total_expenses(df1)
        df2_expenses, _ = self.total_expenses(df2)
        
        diff = {}
        for categorie in self.categories:
            diff[categorie] =(2*int(df1_lastest)-1)*(df1_expenses[categorie]- df2_expenses[categorie])
        return diff
    
    def info_labeled(self):
        None_idx = self.data['Transaction Label'].value_counts().index.to_list().index('None')
        transaction_label_vals = self.data['Transaction Label'].value_counts().values[None_idx]       
        print('In total',
              "{:.2f}".format((1-transaction_label_vals/self.data['Transaction Label'].shape[0])*100),
              "% of all transactions have been labels.")
        print('')
        
    def load_keywords_from_db(self, path='database.db'):
        extenstions = ['.bak', '.dat', '.dir']
        if all(list(map(lambda x: Path(path+x).is_file(),extenstions))):
        #with shelve.open(path) as database:
            database = shelve.open(path)
            self.db = dict(database)
            
        else:
            print('Could not find a file under the given path:', path)
            raise ValueError('Could not find a file under the given path: ' + path)
    
    def save_data(self,path):
        self.data.to_csv(path,sep=';',quoting=int(True), encoding ='latin-1')   
        
        with open(path, "r") as f:
            lines = f.readlines()
            
        with open(path, "w") as f:
            for line in self.meta_data_lines:
                f.write(line)
            for line in lines:
                f.write(line)
        
      
    def erase_meta_data(self):
        with open(self.data_latest_file, "r") as f:
            lines = f.readlines()
    
        header_idx = -1
        for i, line in enumerate(lines):
            if np.min([line.find('Buchungstag'),line.find('Wertstellung'),line.find('BLZ')])> -1:
                header_idx = i
        
        if header_idx > -1:
            self.meta_data_lines = lines[:header_idx]
            lines = lines[header_idx:-1]
        
        with open(self.data_latest_file + 'wo_meta.csv', "w") as f:
            for line in lines:
                f.write(line)
        return self.data_latest_file + 'wo_meta.csv'

'''
def label_row(self):
        counter = 0
        for idx, row in self.data.iterrows():
            if counter+1 == 2:
                break
            else:
                row_df = pd.DataFrame(row).T
                if is_income(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'Salary'
                elif is_grocery(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'Groceries'
                elif is_dining(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'Dining'
                elif is_amazon(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'Amazon'
                elif is_miete(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'Rent'
                elif is_mobil(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'Mobil phone / Internet'
                elif is_travel(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'Travel'
                elif is_credit_card(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'Credit card'
                elif is_fuel(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'Fuel'
                elif is_insurance(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'Insurance'
                elif is_EoQuartal(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'End of quater'
                elif is_culture(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'Culture'
                elif is_pharmacy(row_df).values[0]:
                    self.data.loc[idx,'Transaction Label'] = 'Pharmacy'
'''