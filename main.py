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

    ba = BankAccounts.DKB('1036976429_v4.csv', pre_labeled=True)


if __name__ == '__main__':
    main()