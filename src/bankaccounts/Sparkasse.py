# -*- coding: utf-8 -*-
"""
Created on Fri Apr 21 16:25:19 2020

@author: LUL3FE
"""

import numpy as np
import pandas as pd
from pandas.plotting import register_matplotlib_converters
import parameters as pm
import BankAccount as base


class Sparkasse(base.BankAccount):
    def __init__(self,
                 current_balance,
                 file: str,
                 pre_labeled: bool = False,
                 keywords_file='database/keywords.json',
                 encoding='latin_1'):
        register_matplotlib_converters()
        super().__init__(encoding=encoding,
                         keywords_file=keywords_file,
                         file=replace_german_umlauts(file, encoding),
                         pre_labeled=pre_labeled)
        print('')

        self.current_balance = current_balance

        self.Sparkasse_header_unlabeled_list = ['Auftragskonto', 'Buchungstag', 'Valutadatum', 'Buchungstext',
                                                'Verwendungszweck', 'Glaeubiger ID', 'Mandatsreferenz',
                                                'Kundenreferenz (End-to-End)', 'Sammlerreferenz',
                                                'Lastschrift Ursprungsbetrag', 'Auslagenersatz Ruecklastschrift',
                                                'Beguenstigter/Zahlungspflichtiger', 'Kontonummer/IBAN',
                                                'BIC (SWIFT-Code)', 'Betrag', 'Waehrung', 'Info']

        self.Sparkasse_header_labeled_list = self.Sparkasse_header_unlabeled_list.copy()
        self.Sparkasse_header_labeled_list.extend(['Balance', 'Transaction Label'])

        self.Sparkasse_header_unlabeled = set(self.Sparkasse_header_unlabeled_list.copy())
        self.Sparkasse_header_labeled = set(self.Sparkasse_header_labeled_list.copy())

        # set type of column 'Betrag' to np. float 
        col_types = {'Betrag': np.float}

        if self.check_trans_n_balance_col():
            self.data = pd.read_csv(self.file,
                                    delimiter=';',
                                    encoding=self.encoding,
                                    usecols=self.Sparkasse_header_labeled,
                                    parse_dates=['Buchungstag', 'Valutadatum'],
                                    dtype=col_types,
                                    decimal=',',
                                    thousands='.',
                                    engine='python',
                                    header=0,
                                    names=self.Sparkasse_header_labeled_list)
        else:
            self.data = pd.read_csv(self.file,
                                    delimiter=';',
                                    encoding=self.encoding,
                                    usecols=self.Sparkasse_header_unlabeled,
                                    parse_dates=['Buchungstag', 'Valutadatum'],
                                    dtype=col_types,
                                    decimal=',',
                                    thousands='.',
                                    engine='python',
                                    header=0,
                                    names=self.Sparkasse_header_unlabeled_list)

        del self.data['Auftragskonto']
        del self.data['Mandatsreferenz']
        del self.data['Sammlerreferenz']
        del self.data['Lastschrift Ursprungsbetrag']
        del self.data['Auslagenersatz Ruecklastschrift']
        del self.data['BIC (SWIFT-Code)']
        del self.data['Waehrung']
        del self.data['Info']

        self.data.rename(columns={
                        'Valutadatum':                         'Werstellung',
                        'Kundenreferenz (End-to-End)':         'Kundenreferenz',
                        'Beguenstigter/Zahlungspflichtiger':   'Auftraggeber / Beguenstigter',
                        'Kontonummer/IBAN':                    'Kontonummer',
                        'Betrag':                              'Betrag (EUR)'},
                        inplace=True)

        self.data = self.add_balance_col(self.data)

        self.daily_data = self.data[['Wertstellung', 'Betrag (EUR)']].groupby('Wertstellung',
                                                                              sort=False).sum().reset_index()
        self.daily_data = self.add_balance_col(self.daily_data)

        self.daily_data = self.update_daily()

        if not self.pre_labeled:
            self.data = self.label_rows(self.data)

        print('')
        self.info_labeled(self.data)

        self.start_date = min(self.data['Wertstellung'])
        self.end_date = max(self.data['Wertstellung'])

        del self.data['index']
        print(pm.dashed_line)
