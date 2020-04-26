import sys
from datetime import datetime, timedelta
sys.path.insert(0,'./src')
sys.path.insert(0,'./src/utils')
sys.path.insert(0,'./src/plotting')
sys.path.insert(0,'./src/bankaccounts')
sys.path.insert(0,'./src/tests')

import BankAccounts


def main():

    # Create a bank account and label it based on pre-defined rules

    ba = BankAccounts.DKB('/home/luis/Documents/1036976429.csv',
                          keywords_file='/home/luis/git/Bank-account-parser/database/keywords.json',
                          pre_labeled=False)


if __name__ == '__main__':
    main()