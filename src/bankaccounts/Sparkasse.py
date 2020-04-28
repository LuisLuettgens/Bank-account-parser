# -*- coding: utf-8 -*-
"""
Created on Fri Apr 21 16:25:19 2020

@author: LUL3FE
"""

import numpy as np
import pandas as pd
from pandas.plotting import register_matplotlib_converters

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
                         file=self.replace_german_umlauts(file, encoding))
        print('')

        self.current_balance = current_balance
        self.pre_labeled = pre_labeled

        use_cols = ['Auftragskonto', 'Buchungstag', 'Valutadatum', 'Buchungstext', 'Verwendungszweck',
                    'Glaeubiger ID', 'Mandatsreferenz', 'Kundenreferenz (End-to-End)', 'Sammlerreferenz',
                    'Lastschrift Ursprungsbetrag', 'Auslagenersatz Ruecklastschrift',
                    'Beguenstigter/Zahlungspflichtiger', 'Kontonummer/IBAN', 'BIC (SWIFT-Code)', 'Betrag',
                    'Waehrung', 'Info']

        # set type of column 'Betrag' to np. float 
        col_types = {'Betrag': np.float}

        self.data = pd.read_csv(self.file,
                                delimiter=';',
                                encoding=self.encoding,
                                usecols=set(use_cols),
                                parse_dates=['Buchungstag', 'Valutadatum'],
                                dtype=col_types,
                                decimal=',',
                                thousands='.',
                                engine='python',
                                header=0,
                                names=use_cols)

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
            self.label_rows()

        print('')
        self.info_labeled()

        self.start_date = min(self.data['Wertstellung'])
        self.end_date = max(self.data['Wertstellung'])

        del self.data['index']
        print(pm.dashed_line)