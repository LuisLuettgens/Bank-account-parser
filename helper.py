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
import shelve

# Konvertiert einen String in ein Datum (Datum im DKB-Format)

def american_format_to_DBK(x):
    x_split = x.split('-')
    x_split[0], x_split[2] = x_split[2], x_split[0]
    return '.'.join(x_split)

def is_date(x):
    if re.match(r'\d{4}-\d{2}-\d{2}', x[0]):
        x = x.apply(lambda x: american_format_to_DBK(x))
    x = pd.to_datetime(x, format='%d.%m.%Y')
    return x
    
# Konvertiert einen String in eine Zahl
def is_float64(x):
    remove_dots          = lambda s: str(s).replace('.','')
    replace_comma_by_dot = lambda s: str(s).replace(',','.')
    float_func           = lambda s: float(s)
    x = list(map(remove_dots,x))
    x = list(map(replace_comma_by_dot,x))
    x = list(map(float_func,x))
    return x

def set_date(year,month,day,hour,minute,second):
    return datetime(year, month, day, hour, minute, second)

def get_month(data, month,year, use_Werstellung = True):
    if use_Werstellung:
        return data[
                        (data['Wertstellung'] >= set_date(year,month,1,0,0,0) )&
                        (data['Wertstellung'] <= set_date(year,month+1,1,0,0,0))
                    ]
    else:
        return data[
                        (data['Buchungstag'] >= set_date(year,month,1,0,0,0) )&
                        (data['Buchungstag'] <= set_date(year,month+1,1,0,0,0))
                    ]

def add_balance_col(data, current_balance):
    s = [current_balance]
    for i, transaction in enumerate(reversed(data['Betrag (EUR)'])):
        s.append(s[i]-transaction)
    del s[-1]
    s.reverse()
    data['Balance'] = s
    return data

def prep_table(data, current_balance): 
    print('Converting Buchungstag to date fomat...\t\t\t', end='')
    data['Buchungstag'] = is_date(data['Buchungstag'])
    print('done!')
    print('Converting Wertstellung to date fomat...\t\t', end='')
    data['Wertstellung'] = is_date(data['Wertstellung'])
    print('done!')
    print('Converting Betrag (EUR) to a float column fomat...\t', end='')
    data['Betrag (EUR)'] = is_float64(data['Betrag (EUR)'])
    print('done!')
    print('Sorting the table based on Wertstellung-column...\t', end='')
    data = data.sort_values(by='Wertstellung')
    data = data.reset_index()
    print('done!')
    
    if 'Transaction Label' not in data.columns:
        print('Adding a transaction label column...\t\t\t', end='')
        data['Transaction Label'] = 'None'
        print('done!')
        
    if 'Balance' not in data.columns:
        print('Adding a column with the daily balance...\t\t', end='')
        data = add_balance_col(data, current_balance)
        print('done!')
        
    return data

def search_for_relevant_columns(col_names):
    if 'Buchungstag' not in col_names:
        return False, 'Buchungstag'
    if 'Wertstellung' not in col_names:
        return False, 'Wertstellung' 
    if 'Buchungstext' not in col_names:
        return False, 'Buchungstext'
    if 'Auftraggeber / Begünstigter' not in col_names:
        return False, 'Auftraggeber / Begünstigter'
    if 'Verwendungszweck' not in col_names:
        return False, 'Verwendungszweck'
    if 'Kontonummer' not in col_names:
        return False, 'Kontonummer'
    if 'BLZ' not in col_names:
        return False, 'BLZ'
    if 'Betrag (EUR)' not in col_names:
        return False, 'Betrag (EUR)'
    if 'Gläubiger-ID' not in col_names:
        return False, 'Gläubiger-ID'
    if 'Mandatsreferenz' not in col_names:
        return False, 'Mandatsreferenz'
    if 'Kundenreferenz' not in col_names:
        return False, 'Kundenreferenz'
    return True, ''

def valid_table(data,current_balance):
    print('Checking whether table is in expcted DKB-format...\t', end='')
    result, name = search_for_relevant_columns(data.columns)
    if not result:
        raise ValueError(name + ' does not appear as a column. Please make sure that it exists and try again...')
    else:
        print('done!')
        pd.set_option('display.max_columns', None)
        data = prep_table(data, current_balance)
        return data
 
def is_valid_csv_file(path):
    my_file = Path(path)
    if not my_file.is_file():
        user_input = input('The path: ' + path + ' cannot be resolved to a valid file. Do you want to continue anyways? [y/n]... ')
        if user_input not in ['y', 'Y', 'yes', 'ja', 'Ja']:
            return False
    else:
        pattern = r'\.csv$'
        if re.search(pattern, path) is None:
            user_input = input('The passed file does not appear to be a csv file. Do you want to continue anyways? [y/n]... ' )
            if user_input not in ['y', 'Y', 'yes', 'ja', 'Ja']:
                return False
    return True

def get_meta_info(path):
    d={}
    with open(path, "r") as f:
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
    d['Balance']  = current_balance_line_spltd[0]
    d['Currency'] = current_balance_line_spltd[1]
    
    IBAN_pattern = r'[\d|\w]+'
    current_balance_line = re.findall(IBAN_pattern, IBAN_line)
    d['IBAN']    = current_balance_line[1]
    d['BA_type'] = current_balance_line[2]
    return d

def erase_meta_data(path):
    with open(path, "r") as f:
        lines = f.readlines()

    header_idx = -1
    for i, line in enumerate(lines):
        if np.min([line.find('Buchungstag'),line.find('Wertstellung'),line.find('BLZ')])> -1:
            header_idx = i
    
    if header_idx > -1:
        meta_info = lines[:header_idx]
        lines = lines[header_idx:-1]
    
    with open(path + 'wo_meta.csv', "w") as f:
        for line in lines:
            f.write(line)
    return path + 'wo_meta.csv'

def n_months_back(n): 
    today = datetime.now()
    
    m = ((today.month - (n+1)) % 12) + 1
    if np.sign(today.month - (n+1)) > - 1:
        y = today.year
    else:
        y = int(np.floor(today.year - (n+1)/12))
    return datetime(y,m,datetime.now().day,datetime.now().hour,datetime.now().minute,datetime.now().second)

def generate_days(first,last):
    step = timedelta(days=1)
    last += timedelta(days=1)
    result = []
    while first < last:
        result.append(pd.Timestamp(first.strftime('%Y-%m-%d %H:%M:%S')))
        #result.append(start)
        first += step
    return result
    
def is_income(df):
    Buchungstext_keywords     = ['Gehalt']
    Verwendungszweck_keywords = ['Unterhalt', 'Semesterbeitrag']
    return (df['Buchungstext'].str.contains("|".join(Buchungstext_keywords),case=False,na=False) |
            df['Verwendungszweck'].str.contains("|".join(Verwendungszweck_keywords),case=False,na=False))

def is_grocery(df):
    Verwendungszweck_keywords = ['REWE']
    Auftraggeber_keywords     = ['REWE', 'EDEKA', 'PENNY', 'KAUFLAND', 'NETTO', 'ALECO GMBH', 'ALDI',
                                 'Lebensmittel', 'LIDL', 'E-CENTER', 'DM FIL', 'ROSSMANN', 'MARKT']
    return (df['Auftraggeber / Begünstigter'].str.contains("|".join(Auftraggeber_keywords),case=False,na=False) |
            df['Verwendungszweck'].str.contains("|".join(Verwendungszweck_keywords),case=False,na=False))
    
def is_dining(df):
    Auftraggeber_keywords     = ['RESTAURANT', 'IMBISS', 'CAFE', 'MCDONALDS', 'SUBWAY', 'Burger King', 'GASTRO',
                                 'VAPIANO', 'BAE?CK', 'LOSTERIA', 'COFFEE', 'SUSHI', 'PIZZA', 'MENSACARD', 'DEAN \+ DAVID']
    return df['Auftraggeber / Begünstigter'].str.contains("|".join(Auftraggeber_keywords),case=False,na=False)

def is_amazon(df):
    Auftraggeber_keywords     = ['AMAZON']
    return df['Auftraggeber / Begünstigter'].str.contains("|".join(Auftraggeber_keywords),case=False,na=False)

def is_miete(df):
    return (df['Verwendungszweck'].str.contains('Miet',case=False,na=False) & 
           (df['Buchungstext'].str.contains('Gutschrift',case=False,na=False) == False))

def is_mobil(df):
    Auftraggeber_keywords     = ['Vodafone', 'Drillisch', 'o2', 'Telekom', '1\&1', 'congstar', 'mobilcom-debitel','Klarmobil']
    return df['Auftraggeber / Begünstigter'].str.contains("|".join(Auftraggeber_keywords),case=False,na=False)


def is_travel(df):
    Auftraggeber_keywords     = ['HOTEL', 'BAHN AG', 'DB AG', 'FERNVERKEHR', 'Motel One', 'JUGENDHERBERG', 'DB VERTRIEB']
    return df['Auftraggeber / Begünstigter'].str.contains("|".join(Auftraggeber_keywords),case=False,na=False)

def is_credit_card(df):
    Auftraggeber_keywords     = ['KREDITKARTENABRECHNUNG', 'DKB VISACARD']
    return df['Auftraggeber / Begünstigter'].str.contains("|".join(Auftraggeber_keywords),case=False,na=False)

def is_fuel(df):
    Auftraggeber_keywords     = ['SHELL', 'Tank', 'ESSO', 'JET', 'AVIA', 'TOTAL Service', 'AGIP','OIL']
    return df['Auftraggeber / Begünstigter'].str.contains("|".join(Auftraggeber_keywords),case=False,na=False)

def is_insurance(df):
    Auftraggeber_keywords     = ['VERSICHERUNG', 'Bundeskasse in Kiel', 'HKK', 'BKK']
    return df['Auftraggeber / Begünstigter'].str.contains("|".join(Auftraggeber_keywords),case=False,na=False)

def is_culture(df):
    Auftraggeber_keywords     = ['Sportverein', 'Turnverein', 'ENTERTAIN', 'SPORT', 'FITNESS', 'CLUB', 'Zeitung']
    return df['Auftraggeber / Begünstigter'].str.contains("|".join(Auftraggeber_keywords),case=False,na=False)
    
def is_EoQuartal(df):
    Buchungstext_keywords=['Abschluss']
    return df['Buchungstext'].str.contains("|".join(Buchungstext_keywords),case=False,na=False)

def is_pharmacy(df):
    Auftraggeber_keywords     = ['APOTHEKE']
    return df['Auftraggeber / Begünstigter'].str.contains("|".join(Auftraggeber_keywords),case=False,na=False)
    

def label_row(df):
    keywords_dict = load_keywords_from_db()
    