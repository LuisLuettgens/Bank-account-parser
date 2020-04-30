# -*- coding: utf-8 -*-
"""
Created on Fri Apr 10 12:52:19 2020

@author: LUL3FE
"""

import os
import re
from datetime import datetime
from typing import List, Tuple

import numpy as np
import pandas as pd
from pandas.plotting import register_matplotlib_converters

import BankAccount as base
import parameters as pm

class DKB(base.BankAccount):
    def __init__(self,
                 file: str,
                 pre_labeled: bool = False,
                 keywords_file='database/keywords.json',
                 encoding='latin_1'):
        register_matplotlib_converters()
        print(pm.calling_DKB_constructor)
        super().__init__(encoding=encoding,
                         keywords_file=keywords_file,
                         file=self.replace_german_umlauts(file, encoding),
                         pre_labeled=pre_labeled)
        meta_data = self.get_meta_info()
        self.iban = meta_data['IBAN']
        self.currency = meta_data['Currency']
        self.current_balance = meta_data['Current balance']
        self.bank_account_type = meta_data['BA_type']

        file_compressed, self.meta_data_lines = self.erase_meta_data()

        self.DKB_header_unlabeled_list = ['Buchungstag', 'Wertstellung', 'Buchungstext', 'Auftraggeber / Beguenstigter',
                                          'Verwendungszweck', 'Kontonummer', 'BLZ', 'Betrag (EUR)', 'Glaeubiger-ID',
                                          'Mandatsreferenz', 'Kundenreferenz']

        self.DKB_header_labeled_list = self.DKB_header_unlabeled_list.copy()
        self.DKB_header_labeled_list.extend(['Balance', 'Transaction Label'])

        self.DKB_header_unlabeled = set(self.DKB_header_unlabeled_list.copy())
        self.DKB_header_labeled = set(self.DKB_header_labeled_list.copy())

        col_types = {'Betrag (EUR)': np.float, 'Balance': np.float}

        self.date_format = '%d.%m.%Y'

        def date_parser_dkb(x):
            return datetime.strptime(str(x), self.date_format)

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

        self.valid_table(tag='DKB')
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

    def get_meta_info(self):
        balance_line = ''
        IBAN_line = ''

        print(pm.layer_prefix + 'Generating meta data...')
        meta_data = {}

        with open(self.file, "r", encoding='latin_1') as f:
            lines = f.readlines()
        IBAN_line_pattern = r'.+Kontonummer.+'
        balance_line_pattern = r'.+Kontostand.+'

        found_IBAN_line = False
        found_balance_line = False

        for line in lines:
            if not found_balance_line and re.findall(balance_line_pattern, line):
                found_balance_line = True
                balance_line = line
            if not found_IBAN_line and re.findall(IBAN_line_pattern, line):
                found_IBAN_line = True
                IBAN_line = line

        if found_balance_line:
            balance_pattern = r'\d{0,7}\.\d{0,3},\d{0,2}\sEUR'
            current_balance_line_split = re.findall(balance_pattern, balance_line)[0].split()
            meta_data['Balance'] = current_balance_line_split[0]
            meta_data['Currency'] = current_balance_line_split[1]

        if found_IBAN_line:
            IBAN_pattern = r'[\d|\w]+'
            current_balance_line = re.findall(IBAN_pattern, IBAN_line)
            meta_data['IBAN'] = current_balance_line[1]
            meta_data['BA_type'] = current_balance_line[2]

            meta_data['Current balance'] = float(meta_data['Balance'].replace('.', '').replace(',', '.'))
        return meta_data

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

    def get_label(self, category: str, start: datetime = None, end: datetime = None) -> pd.DataFrame:
        """
            This function let's you filter self.data for a given category in a time interval. If no start or end time
            are supplied the minimum and maximum are used respectively instead.

        Args:
            self:      An object of the class DKB.
            category:  The label that shall be filtered for
            start:     The start datetime that is used for that query (default = None)
            end:       The end datetime that is used for that query (default = None)


        Returns:
            A DataFrame containing only entries from the closed interval [start, end] with 'Transaction Label' equal to
            category.

        Raises:
            ValueError: Raised when category does not appear in self.labels.

        """
        if start is None:
            start = self.start_date

        if end is None:
            end = self.end_date

        if category not in self.labels:
            raise ValueError('This is not a valid lab   el. Please choose one from the following: ' +
                             ', '.join(self.labels))

        df_trans = self.get_months(start, end, use_daily_table=False)
        return df_trans[df_trans['Transaction Label'] == category]

    def all_labels(self) -> List[str]:
        """
            This functions is a copy of all_categories
        """

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

    def get_row(self, idx: int) -> pd.DataFrame:
        """
            Getter function for rows in self.data
        Args:
            idx: row index

        Returns:
            returns the row with index 'idx' as a DataFrame
        """
        return pd.DataFrame(self.data.iloc[idx]).T

    def erase_meta_data(self) -> Tuple[str, List[str]]:
        """

        Returns:

        """
        with open(self.file, "r", encoding='latin_1') as f:
            lines = f.readlines()

        header_idx = -1
        for i, line in enumerate(lines):
            if np.min([line.find('Buchungstag'), line.find('Wertstellung'), line.find('BLZ')]) > -1:
                header_idx = i

        meta_data_lines = None

        if header_idx > -1:
            meta_data_lines = lines[:header_idx]
            lines = lines[header_idx:]

        with open(self.file + 'wo_meta.csv', "w") as f:
            for line in lines:
                f.write(line)
        return self.file + 'wo_meta.csv', meta_data_lines

    def merge(self, other_path, pre_labeled=False):
        other = DKB(other_path, pre_labeled=pre_labeled)
        self.data = pd.concat([self.data, other.data]).drop_duplicates().reset_index(drop=True)
        self.daily_data = pd.concat([self.daily_data, other.daily_data]).drop_duplicates().reset_index(drop=True)
        pass
