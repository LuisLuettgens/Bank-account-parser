# -*- coding: utf-8 -*-
"""
Created on Fri Apr 21 16:25:19 2020

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


class Sparkasse(base.BankAccount):
    def __init__(self,
                 data_latest_file: str,
                 pre_labeled: bool = False,
                 encoding='latin_1'):
        register_matplotlib_converters()
        super().__init__(encoding)
        print('')
        self.data_latest_file = self.replace_german_umlauts(data_latest_file)

        use_cols = {'Buchungstag','Valutadatum','Buchungstext','Verwendungszweck',
                    'Glaeubiger ID','Mandatsreferenz','Kundenreferenz (End-to-End)',
                                          'Beguenstigter/Zahlungspflichtiger','Kontonummer/IBAN',
                                          'Betrag'}
 
       

        col_types = {'Betrag': np.float}


        self.data = pd.read_csv(self.data_latest_file,
                                        delimiter=';',
                                        encoding=self.encoding,
                                        usecols=use_cols,
                                        parse_dates=['Buchungstag','Valutadatum'],
                                        dtype=col_types,
                                        decimal=',',
                                        thousands='.',
                                        engine='python',
                                        #names=names,
                                        header=0)

        self.data.rename(columns={
                        'Valutadatum' :                         'Werstellung',
                        'Kundenreferenz (End-to-End)' :         'Kundenreferenz',
                        'Beguenstigter/Zahlungspflichtiger' :   'Auftraggeber / Beguenstigter',
                        'Kontonummer/IBAN' :                    'Kontonummer',
                        'Betrag' :                              'Betrag (EUR)'}
                        , inplace=True)
