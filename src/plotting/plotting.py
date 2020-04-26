import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta


def summary(bank_account, start, end):
    # preparation
    df = bank_account.get_months(start, end)
    df_trans = bank_account.get_months(start, end, use_daily_table=False)
    
    # Account balance & transactions
    Wert = df['Wertstellung']
    Bal = df['Balance']
    Betrag = df['Betrag (EUR)']
        
    #TODO divided by zero wgen len wert smaller than 6
    dates = list(Wert[0:-1:int(np.floor(len(Wert)/6))])
    xlabels = [x.date().strftime('%Y-%m-%d') for x in dates]
    
    # Expenses per month plot
    expenses, total_expenses = bank_account.cluster_expenses(*bank_account.total_expenses(df_trans))

    # Compare expenses to previous time period
    diff = (end-start).days

    begin_prev_period = start - timedelta(days=diff+1)
    end_prev_period = start - timedelta(days=1)

    pref_period_trans = bank_account.get_months(begin_prev_period, end_prev_period, use_daily_table=False)
    diff = bank_account.trend_adjacent(df_trans, pref_period_trans)

    # Create plots
    n_rows = 3
    n_cols = 2
    fig, axes = plt.subplots(nrows=n_rows, ncols=n_cols, figsize=(n_cols*10, n_rows*10))
        
    # Accounts balance plot
    axes[0, 0].plot(Wert, Bal)
    axes[0, 0].set_xticklabels(xlabels, rotation=20)
    axes[0, 0].set_title("Temporal progression of the account balance")
    axes[0, 0].set_ylabel("EUR")
    axes[0, 0].xaxis.set_major_locator(plt.MaxNLocator(6))

    # Account transaction
    axes[0, 1].plot(Wert, Betrag)
    axes[0, 1].set_xticklabels(xlabels, rotation=20)
    axes[0, 1].set_title("Temporal progression of transactions")
    axes[0, 1].set_ylabel("EUR")
    
    # Expenses per category
    axes[1, 0].pie(expenses.values(), labels=expenses.keys(), autopct='%1.1f%%', shadow=True, startangle=90)
    axes[1, 0].axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    axes[1, 0].set_title("Expenses per category")

    # Compare with last period
    axes[1, 1].bar(diff.keys(), diff.values())
    axes[1, 1].axhline(y=0.0, color='k', linestyle='-')
    axes[1, 1].set_xticklabels(diff.keys(), rotation=90)
    axes[1, 1].set_ylabel('EUR')
    axes[1, 1].set_title("Change in spent capital per category")
    
    # Income vs Expenses
    total_salary = df_trans.loc[(df_trans['Betrag (EUR)'] > 0) & (df_trans['Transaction Label'] == 'Salary')]
    other_income = df_trans.loc[(df_trans['Betrag (EUR)'] > 0) & (df_trans['Transaction Label'] != 'Salary')]
    expenses = df_trans.loc[(df_trans['Betrag (EUR)'] < 0)]
        
    first = min(df_trans['Wertstellung'])
    last = max(df_trans['Wertstellung'])
        
    current = first
    n_months = 0
    while current < last:
        n_months += 1
        current += relativedelta(months=+1)

    months = []
    salary_slice = []
    other_income_slice = []
    expenses_slice = []

    current_month = first.month
    current_year = first.year

    xlabels_dates = ['']

    for i in range(n_months):
        xlabels_dates.append(str(current_month)+'-'+str(current_year))

        next_month = current_month % 12+1
        next_year = current_year
        if next_month == 1:
            next_year += 1  

        from_date = datetime(current_year, current_month, 1)
        to_date = datetime(next_year, next_month, 1)
            
        months.append(str(first.month) + '-' + str(first.year))
        salary_slice.append(total_salary[(total_salary['Wertstellung'] >= from_date) &
                                         (total_salary['Wertstellung'] < to_date)].sum()['Betrag (EUR)'])
            
        other_income_slice.append(other_income[(other_income['Wertstellung'] >= from_date) &
                                               (other_income['Wertstellung'] < to_date)].sum()['Betrag (EUR)'])
            
        expenses_slice.append(expenses[(expenses['Wertstellung'] >= from_date) &
                                       (expenses['Wertstellung'] < to_date)].sum()['Betrag (EUR)'])
            
        current_month = next_month
        current_year = next_year

    N = n_months
    ind = np.arange(N)    # the x locations for the groups
    width = 0.35       # the width of the bars: can also be len(x) sequence

    axes[2, 0].bar(ind, expenses_slice, width)
    axes[2, 0].bar(ind, salary_slice, width)
    axes[2, 0].bar(ind, other_income_slice, width, bottom=salary_slice)
    axes[2, 0].axhline(0, color='black')
    axes[2, 0].set_title("Income vs. expenses per month")
    axes[2, 0].set_ylabel('EUR')
    axes[2, 0].xaxis.set_major_locator(plt.MaxNLocator(len(xlabels_dates)-1))
    axes[2, 0].set_xticklabels(xlabels_dates)
    plt.legend(['Expenses', 'Salary', 'Other Income'])
        
    # Set title
    title = "".join(['Summary for period: ', start.date().strftime('%Y-%m-%d'), ' - ', end.date().strftime('%Y-%m-%d')])
    fig.suptitle(title, fontsize=16)
    return True
