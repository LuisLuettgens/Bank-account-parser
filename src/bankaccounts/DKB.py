# -*- coding: utf-8 -*-
"""
Created on Fri Apr 10 12:52:19 2020

@author: LUL3FE
"""

import functools
import os
from datetime import datetime
from typing import List

import numpy as np
import pandas as pd
from pandas.plotting import register_matplotlib_converters

import BankAccount as base
import helper as helper
import parameters as pm



class DKB(base.BankAccount):
    def __init__(self,
                 file: str,
                 pre_labeled: bool = False,
                 keywords_file='database/keywords.json',
                 encoding='latin_1'):
        register_matplotlib_converters()
        print(pm.calling_DKB_constructor)
        super().__init__(encoding=encoding, keywords_file=keywords_file)
        self.file = self.replace_german_umlauts(file)
        self.dfs = []
        self.get_meta_info()
        self.pre_labeled = pre_labeled
        file_compressed = self.erase_meta_data()

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

        with open(file, "r", encoding=self.encoding) as f:
            lines = f.readlines()

        for line in lines:
            if self.has_balance_col and self.has_transaction_label_col:
                break
            if 'Balance' in line:
                self.has_balance_col = True
            if 'Transaction Label' in line:
                self.has_transaction_label_col = True

        if self.has_balance_col and self.has_transaction_label_col:
            self.data = pd.read_csv(file_compressed,
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
                                    names=self.DKB_header_labeled_list)
        else:
            self.data = pd.read_csv(file_compressed,
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
                                    names=self.DKB_header_unlabeled_list)

        os.remove(file_compressed)

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
        print(pm.dashed_line)

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
        print(pm.layer_prefix+'Sorting the table based on Wertstellung-column...')
        self.data = self.data.sort_values(by=sort_by, ascending=ascending)
        self.data = self.data.reset_index()

        if 'Transaction Label' not in self.data.columns:
            print(pm.layer_prefix+'Adding a transaction label column...')
            self.data['Transaction Label'] = 'None'

        if 'Balance' not in self.data.columns:
            print(pm.layer_prefix+'Adding a column with the daily balance...')
            self.data = self.add_balance_col(self.data)

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
        print(pm.layer_prefix+'Checking whether table is in expected DKB-format...')

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
            print('')
        else:
            None_idx = list(self.data['Transaction Label'].value_counts().index).index('None')
            transaction_label_values = self.data['Transaction Label'].value_counts().values[None_idx]

            print('In total',
                  "{:.2f}".format((1 - transaction_label_values / self.data['Transaction Label'].shape[0]) * 100)
                  , "% of all transactions have labels.")

            print('')

    def get_label(self, category: str, start: datetime = None, end: datetime = None) -> pd.DataFrame:
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
            ValueError: Raised when category does not appear in self.labels.

        """
        if start is None:
            start = self.start_date

        if end is None:
            end = self.end_date

        if category not in self.labels:
            raise ValueError('This is not a valid label. Please choose one from the following: ' + ', '.join(self.labels))

        df_trans = self.get_months(start, end, use_daily_table=False)
        return df_trans[df_trans['Transaction Label'] == category]

    def all_labels(self) -> List[str]:
        "This functions is a copy of all_categories"
        return self.labels

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
