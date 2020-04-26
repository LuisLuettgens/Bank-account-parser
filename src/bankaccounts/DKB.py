# -*- coding: utf-8 -*-
"""
Created on Fri Apr 10 12:52:19 2020

@author: LUL3FE
"""

import functools
import os
import shelve
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from pandas.plotting import register_matplotlib_converters

import BankAccount as base
import helper as helper

import matplotlib
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta
import database  as database

class DKB(base.BankAccount):
    def __init__(self,
                 data_latest_file: str,
                 pre_labeled: bool = False,
                 other_data_files: List[str] = [],
                 database='database/database.db',
                 encoding='latin_1'):
        register_matplotlib_converters()
        super().__init__(encoding)
        print('')
        self.data_latest_file = self.replace_german_umlauts(data_latest_file)
        self.data_other_files = other_data_files
        self.dfs = []
        self.get_meta_info()
        self.database = database
        self.load_keywords_from_db(self.database)
        print('Loading new database...\t\t\t', end='')
        self.keywords = '/home/luis/git/Bank-account-parser/database/keywords.json'
        print(self.keywords)
        self.new_db = database.Database(self.keywords)
        print('done!')
        self.pre_labeled = pre_labeled
        latest_data_file_compressed_path = self.erase_meta_data()

        self.DKB_header_unlabeled_list = ['Buchungstag', 'Wertstellung', 'Buchungstext', 'Auftraggeber / Beguenstigter',
                                          'Verwendungszweck', 'Kontonummer', 'BLZ', 'Betrag (EUR)', 'Glaeubiger-ID',
                                          'Mandatsreferenz', 'Kundenreferenz']

        self.DKB_header_labeled_list = self.DKB_header_unlabeled_list.copy()
        self.DKB_header_labeled_list.extend(['Balance', 'Transaction Label'])

        self.DKB_header_unlabeled = set(self.DKB_header_unlabeled_list.copy())
        self.DKB_header_labeled = set(self.DKB_header_labeled_list.copy())

        col_types = {'Betrag (EUR)': np.float, 'Balance': np.float}

        self.date_format = '%d.%m.%Y'
        date_parser_dkb = lambda x: datetime.strptime(str(x), self.date_format)

        self.has_transaction_label_col = False
        self.has_balance_col = False

        with open(data_latest_file, "r", encoding=self.encoding) as f:
            lines = f.readlines()

        for line in lines:
            if 'Balance' in line:
                self.has_balance_col = True
            if 'Transaction Label' in line:
                self.has_transaction_label_col = True

        if self.has_balance_col and self.has_transaction_label_col:
            self.dfs.append(pd.read_csv(latest_data_file_compressed_path,
                                        delimiter=';',
                                        encoding=self.encoding,
                                        usecols=self.DKB_header_labeled,
                                        parse_dates=['Buchungstag', 'Wertstellung'],
                                        date_parser=date_parser_dkb,
                                        dtype=col_types,
                                        decimal=',',
                                        thousands='.',
                                        engine='python',
                                        header=0,
                                        names=self.DKB_header_labeled_list))
        else:
            self.dfs.append(pd.read_csv(latest_data_file_compressed_path,
                                        delimiter=';',
                                        encoding=self.encoding,
                                        usecols=self.DKB_header_unlabeled,
                                        parse_dates=['Buchungstag', 'Wertstellung'],
                                        date_parser=date_parser_dkb,
                                        dtype=col_types,
                                        decimal=',',
                                        thousands='.',
                                        engine='python',
                                        header=0,
                                        names=self.DKB_header_unlabeled_list))

        os.remove(latest_data_file_compressed_path)

        for data_file in self.data_other_files:
            print('Parsing file: ' + data_file + '...\t\t\t', end='')
            helper.is_valid_csv_file(data_file)
            self.dfs.append(pd.read_csv(helper.erase_meta_data(data_file), delimiter=';', encoding=self.encoding))
            print('done!')

        append_ignore_idx = functools.partial(pd.DataFrame.append, ignore_index=True)

        self.data = functools.reduce(append_ignore_idx, self.dfs)
        self.valid_table()
        self.data = self.add_balance_col(self.data)

        self.daily_data = self.data[['Wertstellung', 'Betrag (EUR)']].groupby('Wertstellung',
                                                                              sort=False).sum().reset_index()
        self.daily_data = self.add_balance_col(self.daily_data)

        self.daily_data = self.update_daily()

        if not self.pre_labeled:
            self.label_rows()

        print('')
        self.info_labeled()

        self.start_date = min(self.data['Wertstellung'])
        self.end_date = max(self.data['Wertstellung'])

        del self.data['index']

    def prep_table(self, sort_by='Wertstellung', ascending=False) -> None:
        """
        This function sorts self.data by the column with name sort_by. If the entries don't have a label a 'Transaction
        Label' column is added to self.data and calls self.add_balance_col
            
        Args:
            self:      An object of the class DKB
            sort_by:   Column name by which the table shall be sorted (default = 'Wertstellung')
            ascending: Sorting order (default= descending)
                
        Returns:
            None
        """
        print('Sorting the table based on Wertstellung-column...\t', end='')
        self.data = self.data.sort_values(by=sort_by, ascending=ascending)
        self.data = self.data.reset_index()
        print('done!')

        if 'Transaction Label' not in self.data.columns:
            print('Adding a transaction label column...\t\t\t', end='')
            self.data['Transaction Label'] = 'None'
            print('done!')

        if 'Balance' not in self.data.columns:
            print('Adding a column with the daily balance...\t\t', end='')
            self.data = self.add_balance_col(self.data)
            print('done!')

    def valid_table(self) -> None:
        """
        This function checks whether all expected column names appear in self.data and calls self.prep_table() afterwards.
        
        Args:
            self:    An object of the class DKB
            
        Returns:
            None
        Raises:
            ValueError: Raised when one of the column names is missing.
        """
        print('Checking whether table is in expected DKB-format...\t', end='')

        if self.pre_labeled:
            missing_cols = self.DKB_header_labeled.difference(self.data.columns)
        else:
            missing_cols = self.DKB_header_unlabeled.difference(self.data.columns)

        if len(missing_cols) == 1:
            raise ValueError('The column: ' + ', '.join(
                missing_cols) + ' does not appear as a column name in the provided csv. Please make sure that '
                                'it exists and try again...')
        ##
        if len(missing_cols) > 1:
            raise ValueError('The columns: ' + ', '.join(
                missing_cols) + ' do not appear as a column names in the provided csv. Please make sure that '
                                'it exists and try again...')

        print('done!')

        pd.set_option('display.max_columns', None)
        self.prep_table()

    def info_labeled(self) -> None:
        """
        This function prints the ratio of labeled entries in the DataFrame.
        
        Args:
            self:    An object of the class DKB
            
        Returns:
            None
        """
        
        if 'None' not in self.data['Transaction Label'].value_counts().index:
            print('In total', "{:.2f}".format(100), "% of all transactions have labels.")
            if 'None' in self.categories:
                self.categories.remove('None')
            print('')
        else:
            None_idx = list(self.data['Transaction Label'].value_counts().index).index('None')
            transaction_label_values = self.data['Transaction Label'].value_counts().values[None_idx]

            print('In total',
                  "{:.2f}".format((1 - transaction_label_values / self.data['Transaction Label'].shape[0]) * 100)
                  , "% of all transactions have labels.")

            print('')

    def get_category(self, category: str, start: datetime = None, end: datetime = None) -> pd.DataFrame:
        """
            This function let's you filter self.data for a given category in a time interval. If no start or end time
            are supplied the minimum and maximum are used respectively instead.
        
        Args:
            self:      An object of the class DKB.
            category: The label that shall be filtered for
            start:     The start datetime that is used for that query (default = None)
            end:       The end datetime that is used for that query (default = None)
            
            
        Returns:
            A DataFrame containing only entries from the closed interval [start, end] with 'Transaction Label' equal to categorie.

        Raises:
            ValueError: Raised when category does not appear in self.categories.
        
        """
        if start is None:
            start = self.start_date

        if end is None:
            end = self.end_date

        if category not in self.categories:
            raise ValueError(
                'This is not a valid label. Please choose one from the following: ' + ', '.join(self.categories))

        df_trans = self.get_months(start, end, use_daily_table=False)
        return df_trans[df_trans['Transaction Label'] == category]

    def load_keywords_from_db(self, path: str = '') -> None:
        """
        This function load a database from 'path' and it as a dictonary of dictonaries in self.db. The keys of self.db are the known categories.
        furthermore three categories: 'Rent', 'None' and 'Private' added.
        
        Args:
            self: An object of the class DKB.
            path: path to the database file (default = database.db)   
            
        Returns:
            None
        Raises:
            ValueError: Raised when one of the files: database.db.bak, database.db.dat or database.db.dir are missing.
        """
        if path == '':
            path = self.database
        extensions = ['.bak', '.dat', '.dir']
        if all(list(map(lambda x: Path(path + x).is_file(), extensions))):
            database = shelve.open(path)
            self.db = dict(database)
            self.categories = list(self.db.keys())
            self.categories.extend(['Rent', 'None', 'Private'])
        else:
            raise ValueError('Could not find a file under the given path: ' + path)

    def all_categories(self) -> List[str]:
        """
            This function returns all known categories of the DKB-object.
        Returns:
            All known categories ('Transaction Labels') as a list of strings
        """
        return self.categories

    def save_data(self, path: str) -> bool:
        """
            This function creates a new csv file based on the current status of the DataFrame: self.data. The format of
            the csv matches the expected formatting of the constructor of the DKB-object.
        Args:
            path: Location where the DataFrame shall be stored to.

        Returns:
            True if the saving process was successful
        """

        self.data.to_csv(path,
                         sep=';',
                         quoting=int(True),
                         encoding=self.encoding,
                         date_format=self.date_format,
                         columns=self.DKB_header_labeled_list,
                         index=False,
                         decimal=',')

        with open(path, "r", encoding='latin_1') as f:
            lines = f.readlines()

        with open(path, "w", encoding='latin_1') as f:
            for line in self.meta_data_lines:
                f.write(line)
            for line in lines:
                f.write(line)

        print('The data was successfully saved under this path:', path)
        return True

    def label_rows(self, path: str = '') -> bool:
        """
        This function adds labels to each transaction in self.data. Basis is the keyword database. Previously labeled
        entries are not labeled again. So far the keywords stored in the database file are concatenated via 'or/|',
        this implies any labeling rule that uses 'and/&' has to be added manually like it is done with the label 'Rent'.

        Args:
            path location where the database is stored

        Returns:
            True if the labeling was successful

        Raises:
            ValueError: When no matching file can be found at the input path

        """
        print('Adding labels to transactions...\t\t\t', end='')
        if path == '':
            path = self.database
        self.load_keywords_from_db(path)
        for idx, row in self.data.iterrows():
            row_df = pd.DataFrame(row).T

            if row_df.loc[idx, 'Transaction Label'] != 'None':
                continue
            else:
                for key in (self.db).keys():
                    label = key
                    for cat_key in self.db[key].keys():
                        col_name = cat_key
                        if row_df[col_name].str.contains("|".join(self.db[key][cat_key]), case=False, na=False).values[
                            0]:
                            self.data.loc[idx, 'Transaction Label'] = label

                if helper.is_rent(row_df).values[0]:
                    self.data.loc[idx, 'Transaction Label'] = 'Rent'
        print('done!')
        return True

    def add_balance_col(self, data: pd.DataFrame) -> pd.DataFrame:
        """
            Based on the self.current_balance and the transactions in columns 'Betrag (EUR)' of data the balance for
            each row is reverse engineered.
        Args:
            data: the DataFrame that shall be augmented with a 'Balance' column

        Returns:
            The input DataFrame with an additional column named 'Balance'

        Raises:
            An KeyError when the input DataFrame has no column with name 'Betrag (EUR)'.
        """

        if 'Betrag (EUR)' not in data.columns:
            raise KeyError(
                'The input DataFrame has no column named: ' + 'Betrag (EUR)' + '. Please make sure it exists.')
        
        s = [self.current_balance]
        for i, transaction in enumerate(data['Betrag (EUR)']):
            s.append(s[i] - transaction)
        del s[-1]
        data['Balance'] = s
        return data

    def get_row(self, idx: int) -> pd.DataFrame:
        """
            Getter function for rows in self.data
        Args:
            idx: row index

        Returns:
            returns the row with index 'idx' as a DataFrame
        """
        return pd.DataFrame(self.data.iloc[idx]).T

    def change_category(self, old: str, new: str) -> bool:
        # TODO: sync changes with database
        # TODO: looks like they are not working properly
        """
            changes all labels from a category to the new label
        Args:
            old: old label
            new: new label

        Returns:
            True if the changing was successful

        Raises:
            KeyError: If old is not a member of data.columns
        """
        self.data.loc[self.data['Transaction Label'] == old, 'Transaction Label'] = new
        self.load_keywords_from_db(self.database)
        return True

    def load_keywords_from_db(self, path: str = '') -> None:
        """
        This function load a database from 'path' and it as a dictonary of dictonaries in self.db. The keys of self.db are the known categories.
        furthermore three categories: 'Rent', 'None' and 'Private' added.

        Args:
            self: An object of the class DKB.
            path: path to the database file (default = database.db)

        Returns:
            None
        Raises:
            ValueError: Raised when one of the files: database.db.bak, database.db.dat or database.db.dir are missing.
        """
        if path == '':
            path = self.database
        extensions = ['.bak', '.dat', '.dir']
        if all(list(map(lambda x: Path(path + x).is_file(), extensions))):
            database = shelve.open(path)
            self.db = dict(database)
            self.categories = list(self.db.keys())
            self.categories.extend(['Rent', 'None', 'Private'])
        else:
            raise ValueError('Could not find a file under the given path: ' + path)

    def add_category(self, category: str, path: str = '') -> bool:
        # TODO: looks like they are not working properly
        """
                This function deletes a category from the database
                Args:
                    path: path to database (default = self.database)
                    category: name of the category that shall be removed

                Returns:
                    True if the deletion was successful
        """
        if path == '':
            path = self.database
        database = shelve.open(path)
        database[category] = {}
        database.sync()
        print(list(database.keys()))
        database.close()
        return True

    def pop_category(self, category: str, path: str = '') -> bool:
        # TODO: looks like they are not working properly
        """
        This function deletes a category from the database
        Args:
            path: path to database (default = self.database)
            category: name of the category that shall be removed

        Returns:
            True if the deletion was successful
        """
        if path == '':
            path = self.database
        database = shelve.open(path)
        database.pop(category, None)
        database.sync()
        print(list(database.keys()))
        database.close()
        self.load_keywords_from_db(self.database)

    def change_category_in_db(self, old: str, new: str, path: str = '') -> None:
        """
        This function load a database from 'path' and it as a dictonary of dictonaries in self.db. The keys of self.db are the known categories.
        furthermore three categories: 'Rent', 'None' and 'Private' added.

        Args:
            old:  old category label
            new:  new category label
            self: An object of the class DKB.
            path: path to the database file (default = database.db)

        Returns:
            None
        Raises:
            ValueError: Raised when one of the files: database.db.bak, database.db.dat or database.db.dir are missing.
        """
        if path == '':
            path = self.database
        extensions = ['.bak', '.dat', '.dir']
        if all(list(map(lambda x: Path(path + x).is_file(), extensions))):
            database = shelve.open(path)
            database[new] = database[old]
            self.categories = list(self.db.keys())
            self.categories.extend(['Rent', 'None', 'Private'])
            self.load_keywords_from_db()
            self.change_category(old, new)
            user_input = input('Do you want to delete the category: ' + old + '[y/n]')
            if user_input in ['y', 'Y', 'yes', 'ja', 'Ja']:
                self.pop_category(old)
        else:
            raise ValueError('Could not find a file under the given path: ' + path)
