# -*- coding: utf-8 -*-
"""
Created on Wed Apr  8 12:31:58 2020

@author: LUL3FE
"""

import re
from datetime import datetime, timedelta

import pandas as pd

import helper as helper
from plotting import summary
import parameters as pm
import jsonInterpreter as jsonInterpreter


class BankAccount:
    def __init__(self, encoding, keywords_file, file):
        self.file = file

        # TODO correct this
        self.data = pd.DataFrame({})
        self.daily_data = pd.DataFrame({})

        print(pm.layer_prefix+'Calling base class constructor...')
        # set the encoding used for input files
        self.encoding = encoding

        # parse keywords_file
        self.db = jsonInterpreter.Database(keywords_file)
        self.labels = self.db.labels

    def replace_german_umlauts(self, path: str, encoding: str) -> str:
        """
        Creates a new file that is a copy of path, but  all occurrences of german umlauts have been replaced.

        Args:
            path:       path to the file
            encoding:   the encoding used to read the file

        Returns:
            A string to the copy

        """
        chars = {'ö': 'oe', 'Ö': 'Oe', 'ä': 'ae', 'Ä': 'Ae', 'ü': 'ue', 'Ü': 'Ue', 'ß': 'ss'}
        lines = []

        with open(path, "r", encoding=encoding) as f:
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
        return self.daily_data

    def get_months(self, start_date, end_date, use_daily_table=True, use_werstellung=True):
        if use_werstellung:
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

    ################################################################################################
    #
    # PLOTTING
    #
    ################################################################################################

    def summary(self, start: datetime, end: datetime) -> bool:
        return summary(self, start, end)

    def summary_quarter(self, quarter_n_year: str) -> bool:
        if not re.match(r'^Q\d/(\d{4}|\d{2})$', quarter_n_year):
            print('Please enter the quarter in one of the two following formats: QX/YYYY or QX/YY')
            return False

        quarter = quarter_n_year.split('/')[0]
        quarter_i = int(quarter[1])
        if 1 > quarter_i or 4 < quarter_i:
            print(quarter, 'is not feasible. Please enter: Q1, Q2, Q3 or Q4')
            return False

        year_i = int(quarter_n_year.split('/')[1]) % 2000 + 2000

        Q_start = datetime(year_i, (quarter_i-1)*3+1, 1)
        if quarter_i < 4:
            Q_end = datetime(year_i, quarter_i*3+1, 1) - timedelta(days=1)
        else:
            Q_end = datetime(year_i+1, 1, 1) - timedelta(days=1)

        return summary(self, Q_start, Q_end, tag=quarter_n_year)

    def summary_this_quarter(self) -> bool:
        year = str(datetime.now().year)
        quarter = str(datetime.now().month//4+1)
        return self.summary_quarter('Q'+quarter+'/'+year)

    def summary_last_quarter(self) -> bool:
        year = str(datetime.now().year)
        quarter = str(datetime.now().month//4)
        if quarter == 0:
            quarter = '4'
            year = str(int(year)-1)
        return self.summary_quarter('Q'+quarter+'/'+year)

    def summary_month(self, month_n_year: str) -> bool:
        if not re.match(r'^(\d|\d{2})/(\d{4}|\d{2})$', month_n_year):
            print('Please enter the quarter in one of the following formats: MM/YYYY, M/YYYY, MM/YY or M/YY')
            return False

        month = int(month_n_year.split('/')[0])
        year = int(month_n_year.split('/')[1]) % 2000 + 2000
        if 1 > month or 12 < month:
            print(month, 'is not feasible. Please enter a month from 1 to 12')
            return False

        M_start = datetime(year, month, 1)
        if month < 12:
            M_end = datetime(year, month+1, 1) - timedelta(days=1)
        else:
            M_end = datetime(year+1, 1, 1) - timedelta(days=1)
        return summary(self, M_start, M_end, month_n_year)

    def summary_this_month(self) -> bool:
        year = str(datetime.now().year)
        month = str(datetime.now().month)
        return self.summary_month(month+'/'+year)

    def summary_last_month(self) -> bool:
        year = str(datetime.now().year)
        month = str(datetime.now().month-1)
        if month == 0:
            month = '12'
            year = str(int(year)-1)
        return self.summary_month(month+'/'+year)

    ################################################################################################

    def update_daily(self):
        print(pm.layer_prefix+'Updating daily transactions...')
        daily_wertstellung = list(self.daily_data['Wertstellung'])
        start_date = min(daily_wertstellung)
        end_date = max(daily_wertstellung)
        days = helper.generate_days(start_date, end_date)
        df = pd.DataFrame({'Wertstellung': [],
                           'Betrag (EUR)': [],
                           'Balance': []})

        for day in days:
            s = pd.Series({'Wertstellung': day,
                           'Betrag (EUR)': 0,
                           'Balance': None})
            df = df.append(s, ignore_index=True)

        for index, row in self.daily_data.iterrows():
            wert = row['Wertstellung']
            betrag = row['Betrag (EUR)']
            balance = row['Balance']
            idx = df.index[df['Wertstellung'] == wert]
            df.loc[idx, 'Betrag (EUR)'] = betrag
            df.loc[idx, 'Balance'] = balance

        for idx, row in df.iterrows():
            if row['Balance'] is None:
                df.loc[idx, 'Balance'] = df.loc[idx-1, 'Balance']
        return df

    def total_expenses(self, df):
        total_expenses = -df.loc[df['Betrag (EUR)'] < 0].sum()['Betrag (EUR)']
        expenses = {}
        for category in self.labels:
            expenses[category] = -df.loc[(df['Betrag (EUR)'] < 0) &
                                         (df['Transaction Label'] == category)].sum()['Betrag (EUR)']
        return expenses, total_expenses

    def cluster_expenses(self, d, total_expenses, min_quota=0.025):
        d['other'] = 0.
        for key in d.copy().keys():
            if d[key] < min_quota*total_expenses:
                d['other'] += d[key]
                del d[key]
        return d, total_expenses

    def category_expenses(self, df, category):
        return {category: -df.loc[(df['Betrag (EUR)'] < 0) &
                                  (df['Transaction Label'] == category)].sum()['Betrag (EUR)']}

    def get_category(self, category, start, end):
        if category not in self.labels:
            print('ERROR: This is an unknown category!\n')
            print('Choose one of the following categories:')
            for i, cat in enumerate(self.labels):
                print(i, ': ', cat)
            return False

        df_trans = self.get_months(start, end, use_daily_table=False)
        return df_trans[df_trans['Transaction Label'] == category]

    def trend_adjacent(self, df1, df2):
        # assuming they are actually adjacent
        df1_latest = True
        if max(df1['Wertstellung']) < max(df2['Wertstellung']):
            df1_latest = False

        df1_expenses, _ = self.total_expenses(df1)
        df2_expenses, _ = self.total_expenses(df2)

        diff = {}
        for category in self.labels:
            diff[category] = (2*int(df1_latest)-1)*(df1_expenses[category] - df2_expenses[category])
        return diff

    def save_data(self, path):
        self.data.to_csv(path, sep=';', quoting=int(True), encoding='latin-1')

        with open(path, "r") as f:
            lines = f.readlines()

        with open(path, "w") as f:
            for line in self.meta_data_lines:
                f.write(line)
            for line in lines:
                f.write(line)

    def label_rows(self):
        print(pm.layer_prefix+'Adding labels to transactions...')
        for idx, row in self.data.iterrows():
            row_df = pd.DataFrame(row).T
            if row_df.loc[idx, 'Transaction Label'] != 'None':
                continue
            for key in self.db.data.keys():
                label = key
                compose = self.db.data[label]['Compose']
                result_per_column = []
                for col_name in self.db.data[label]:
                    if col_name == 'Compose' or self.db.data[label][col_name] is None:
                        continue
                    result_per_column.append(row_df[col_name].str.contains("|".join(self.db.data[label][col_name]),
                                                                           case=False, na=False).values[0])
                if len(result_per_column) == 0:
                    continue
                if compose == 'and':
                    if all(result_per_column):
                        self.data.loc[idx, 'Transaction Label'] = label
                elif compose == 'or':
                    if any(result_per_column):
                        self.data.loc[idx, 'Transaction Label'] = label
                elif compose is None:
                    if any(result_per_column):
                        self.data.loc[idx, 'Transaction Label'] = label

        return True

    def show_None(self, n: int = 5) -> pd.DataFrame:
        """
        This function returns a random sample from the DataFrame. All entries have 'None' as their 'Transaction Label'.
        Use this function on combination with change_label_by_hand.

        Args:
            self: An object of the class DKB
            n:    The number of returned entries (default = 5)

        Returns:
            Returns the minimum of n and all possible rows without a transaction label as a DataFrame.
       """
        none_entries = self.data[self.data['Transaction Label'] == 'None']
        if none_entries.shape[0] == 0:
            print('No more \'None\'-labeled entries left!')
            return none_entries
        return none_entries.sample(n=min(n, none_entries.shape[0]))

    def change_label(self, row_idx: int, label: str) -> pd.DataFrame:
        """
        This function allows you to change the label of an entry by hand based on the row index. After the entry was
        changed you get asked whether all entries with the same 'Auftraggeber / Begünstigter' get the same label.

        Args:
            self:    An object of the class DKB
            row_idx: The index of the line which shall be changed
            label:   The new label of that entry in the DataFrame

        Returns:
            Shows all the rows that have been changed in the form of a DataFrame

        Raises:
            ValueError: Raised when label is not a string found in self.categories.
        """
        if label not in self.labels:
            raise ValueError("This is not a valid label. Please choose one from the following: '"
                             + ', '.join(self.categories))

        current_label = self.data.loc[row_idx, 'Transaction Label']
        self.data.loc[row_idx, 'Transaction Label'] = label
        counterpart = self.data.loc[row_idx, 'Auftraggeber / Beguenstigter']
        print('Changed the label from: ', current_label, 'to', label, '.')
        output = ' '.join(['Do you want to change all transactions with', counterpart, 'to', label, '?[y/n]\t'])
        user_input = input(output)
        if user_input in ['y', 'Y', 'yes', 'ja', 'Ja']:
            print('Changing all other labels accordingly...')
            for idx in self.data[self.data['Auftraggeber / Beguenstigter'].str.
                    contains(counterpart, case=False, na=False)].index:
                self.data.loc[idx, 'Transaction Label'] = label
            return self.data[self.data['Auftraggeber / Beguenstigter'].str.contains(counterpart, case=False, na=False)]
        return pd.DataFrame(self.data.iloc[row_idx]).T
