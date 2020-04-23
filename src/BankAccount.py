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
from pathlib import Path
import functools
import helper as helper
from pandas.plotting import register_matplotlib_converters
import shelve
from dateutil.relativedelta import relativedelta


class BankAccount:
    def __init__(self,encoding):
        print('Calling base class constructor')
        self.encoding = encoding

    def replace_german_umlauts(self, path: str) -> str:
        """

        Args:
            path:

        Returns:

        """
        chars = {'ö': 'oe',
                 'Ö': 'Oe',
                 'ä': 'ae',
                 'Ä': 'Ae',
                 'ü': 'ue',
                 'Ü': 'Ue',
                 'ß': 'ss'}
        lines = []

        with open(path, "r", encoding=self.encoding) as f:
            lines_local = f.readlines()

            for line in lines_local:
                for char in chars:
                    line = line.replace(char, chars[char])
                lines.append(line)
            f.close()

        with open(path.split('.')[0] + '_copy.csv', "w+", encoding='utf-8') as f:
            for line in lines:
                f.write(line)
        f.close()
        return path.split('.')[0] + '_copy.csv'
    
    def get_data(self):
        return self.data
    
    def get_data_daily(self):
        return self.daily_data()
            
    def get_months(self, start_date, end_date, use_daily_table=True, use_Werstellung = True):
        if use_Werstellung:
            if use_daily_table:
                return self.daily_data[(self.daily_data['Wertstellung'] >= start_date) &
                                       (self.daily_data['Wertstellung'] <= end_date)]
            
            return self.data[(self.data['Wertstellung'] >= start_date) &
                             (self.data['Wertstellung'] <= end_date)]

        if use_daily_table:
            return self.daily_data[(self.daily_data['Buchungstag'] >= start_date) &
                                   (self.daily_data['Buchungstag'] <= end_date)]
    
        return self.data[(self.data['Buchungstag'] >= start_date) &
                         (self.data['Buchungstag'] <= end_date)]
                
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
        
        dates = list(Wert[0:-1:int(np.floor(len(Wert)/6))])
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

        values = np.array(list(results.values()))
        values_cum = values.cumsum(axis=1)
        category_colors = plt.get_cmap('Blues')(
        np.linspace(0.15, 0.85, values.shape[1]))
        
        # Create plots
        nrows = 3
        ncols = 2
        fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(ncols*10, nrows*10))
        
        # Accounts balance plot
        axes[0,0].plot(Wert,Bal)
        axes[0,0].set_xticklabels(xlabels, rotation=20)
        axes[0,0].set_title("Temporal progression of the account balance")
        axes[0,0].set_ylabel("EUR")
        axes[0,0].xaxis.set_major_locator(plt.MaxNLocator(6))

        # Account transaction
        axes[0,1].plot(Wert,Betrag)
        axes[0,1].set_xticklabels(xlabels, rotation=20)
        axes[0,1].set_title("Temporal progression of transactions")
        axes[0,1].set_ylabel("EUR")
        
        # Expenses per category
        axes[1,0].pie(expenses.values(),labels=expenses.keys(), autopct='%1.1f%%',shadow=True, startangle=90)
        axes[1,0].axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        axes[1,0].set_title("Expenses per category")
        
        # Compare with last period
        axes[1,1].bar(diff.keys(),diff.values())
        axes[1,1].axhline(y=0.0, color='k', linestyle='-')
        axes[1,1].set_xticklabels(diff.keys(), rotation=90)
        axes[1,1].set_ylabel('EUR')
        axes[1,1].set_title("Change in spent capital per category")
    
        # Income vs Expenses
        total_salary = df_trans.loc[(df_trans['Betrag (EUR)'] > 0) & (df_trans['Transaction Label'] == 'Salary')]
        other_income = df_trans.loc[(df_trans['Betrag (EUR)'] > 0) & (df_trans['Transaction Label'] != 'Salary')]
        expenses     = df_trans.loc[(df_trans['Betrag (EUR)'] < 0)]
        
        first = min(df_trans['Wertstellung'])
        last  = max(df_trans['Wertstellung'])
        
        current = first
        n_months = 0
        while current < last:
            n_months += 1
            current += relativedelta(months=+1)


        months = []
        salary_slice = []
        other_income_slice = []
        expenses_slice = []

        current_month = first.month
        current_year  = first.year

        xlabels_dates = ['']

        for i in range(n_months):
            xlabels_dates.append(str(current_month)+'-'+str(current_year))

            next_month = (current_month)%12+1
            next_year = current_year
            if next_month == 1:
                next_year += 1  

            from_date = datetime(current_year,current_month,1)
            to_date = datetime(next_year,next_month,1)
            
            months.append(str(first.month) + '-' + str(first.year))
            salary_slice.append(total_salary[(total_salary['Wertstellung']>=from_date)&
                                            (total_salary['Wertstellung']<to_date)].sum()['Betrag (EUR)'])
            
            other_income_slice.append(other_income[(other_income['Wertstellung']>=from_date)&
                                    (other_income['Wertstellung']<to_date)].sum()['Betrag (EUR)'])
            
            expenses_slice.append(expenses[(expenses['Wertstellung']>=from_date)&
                                        (expenses['Wertstellung']<to_date)].sum()['Betrag (EUR)'])
            
            current_month = next_month
            current_year  = next_year

        N = n_months
        ind = np.arange(N)    # the x locations for the groups
        width = 0.35       # the width of the bars: can also be len(x) sequence

        #fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(10, 10))
                
        axes[2,0].bar(ind, expenses_slice, width)
        axes[2,0].bar(ind, salary_slice, width)
        axes[2,0].bar(ind, other_income_slice, width,bottom=salary_slice)
        axes[2,0].axhline(0, color='black')
        axes[2,0].set_title("Income vs. expenses per month")
        axes[2,0].set_ylabel('EUR')
        axes[2,0].xaxis.set_major_locator(plt.MaxNLocator(len(xlabels_dates)-1))
        axes[2,0].set_xticklabels(xlabels_dates)
        plt.legend(['Expenses', 'Salary', 'Other Income'])
        
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
        print('Updatig daily transactions...\t\t\t\t', end='')
        daily_wertstellung = list(self.daily_data['Wertstellung'])
        start_date = min(daily_wertstellung)
        end_date   = max(daily_wertstellung)
        days = helper.generate_days(start_date, end_date)
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
            if row['Balance'] is None:
                df.loc[idx,'Balance'] = df.loc[idx-1,'Balance']
        print('done!')
        return df
    
    def label_rows(self):
        print('Adding labels to transactions...\t\t\t', end='')
        self.load_keywords_from_db()
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
        print('done!')
        
      
    def total_expenses(self, df):
        total_expenses = -df.loc[df['Betrag (EUR)'] < 0].sum()['Betrag (EUR)']
        expenses = {}
        for category in self.categories:
            expenses[category] = -df.loc[(df['Betrag (EUR)'] < 0) & (df['Transaction Label'] == category)].sum()['Betrag (EUR)']
        return expenses, total_expenses
    
    def cluster_expenses(self,d,total_expenses, min_quota = 0.025):
        d['other'] = 0.
        for key in d.copy().keys():
            if d[key] < min_quota*total_expenses:
                d['other'] += d[key]
                del d[key]
        return d, total_expenses
    
    def category_expenses(self, df, category):
        return {category: -df.loc[(df['Betrag (EUR)'] < 0) & (df['Transaction Label'] == category)].sum()['Betrag (EUR)']}
        
    def get_category(self,category,start,end):
        if category not in self.categories:
            print('ERROR: This is an unknown category!\n')
            print('Choose one of the following categories:')
            for i, cat in enumerate(self.categories):
                print(i,': ', cat)
            return False
    
        df_trans = self.get_months(start,end,use_daily_table=False)
        return df_trans[df_trans['Transaction Label'] == category]
    
    def trend_adjacent(self,df1, df2):
        # assuming they are actually adjacent
        df1_lastest = True
        if max(df1['Wertstellung']) < max(df2['Wertstellung']):
            df1_lastest = False
        
        df1_expenses, _ = self.total_expenses(df1)
        df2_expenses, _ = self.total_expenses(df2)
        
        diff = {}
        for category in self.categories:
            diff[category] =(2*int(df1_lastest)-1)*(df1_expenses[category]- df2_expenses[category])
        return diff
       
    def load_keywords_from_db(self, path='database.db'):
        extenstions = ['.bak', '.dat', '.dir']
        if all(list(map(lambda x: Path(path+x).is_file(),extenstions))):
            database        = shelve.open(path)
            self.db         = dict(database)
            self.categories = list(self.db.keys())
            self.categories.append('Rent')
            self.categories.append('None')
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
        with open(self.data_latest_file, "r", encoding='latin_1') as f:
            lines = f.readlines()
    
        header_idx = -1
        for i, line in enumerate(lines):
            if np.min([line.find('Buchungstag'),line.find('Wertstellung'),line.find('BLZ')])> -1:
                header_idx = i
        
        if header_idx > -1:
            self.meta_data_lines = lines[:header_idx]
            lines = lines[header_idx:]
        
        with open(self.data_latest_file + 'wo_meta.csv', "w") as f:
            for line in lines:
                f.write(line)
        return self.data_latest_file + 'wo_meta.csv'
    
    def get_meta_info(self):
        print('Generating meta data...\t\t\t\t\t', end='')
        self.meta_data = {}
        
        with open(self.data_latest_file, "r", encoding='latin_1') as f:
            lines = f.readlines()
        IBAN_line_pattern    = r'.+Kontonummer.+'
        balance_line_pattern = r'.+Kontostand.+'
    
        found_IBAN_line    = False
        found_balance_line = False
    
        for line in lines:
            if not found_balance_line and re.findall(balance_line_pattern, line):
                found_balance_line = True
                balance_line       = line
            if not found_IBAN_line and re.findall(IBAN_line_pattern, line):
                found_IBAN_line = True
                IBAN_line    = line
    
        balance_pattern = r'\d{0,7}\.\d{0,3},\d{0,2}\sEUR'
        current_balance_line_spltd = re.findall(balance_pattern, balance_line)[0].split()
        self.meta_data['Balance']  = current_balance_line_spltd[0]
        self.meta_data['Currency'] = current_balance_line_spltd[1]
        
        IBAN_pattern = r'[\d|\w]+'
        current_balance_line = re.findall(IBAN_pattern, IBAN_line)
        self.meta_data['IBAN']    = current_balance_line[1]
        self.meta_data['BA_type'] = current_balance_line[2]
        
        self.current_balance   = float(self.meta_data['Balance'].replace('.','').replace(',','.'))
        self.currency          = self.meta_data['Currency']
        self.bank_account_type = self.meta_data['BA_type']
        self.IBAN              = self.meta_data['IBAN']
        print('done!')
        