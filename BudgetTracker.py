import sys
import os
from PyQt5.QtSql import QSqlDatabase, QSqlQuery
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QGridLayout, QDateEdit, QComboBox, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QAction, QFileDialog)
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QMessageBox
import pandas as pd  # Import pandas

class BudgetTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Budget Tracker 2.0")
        self.setGeometry(100, 100, 800, 600)

        # Create a tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Create the first tab for item entry and display
        self.create_transaction_entry_tab()
        
        # Create the second tab for accounting details
        self.create_account_details_tab()

        if not self.initialize_db():
            print("Failed to initialize the databases")
            return
        
        # Call this method after initializing the database and setting up the UI components
        self.load_latest_accounting_details()

        # Create the third tab for monthly spending
        self.create_monthly_spending_tab()

        # Refresh the table view in Tab 1 (transaction entry) to show the latest transactions
        self.refresh_ledger_table()

        # Create the fourth tab for Excel file input
        self.import_excel_tab()
        self.setup_menu()
        
    def setup_menu(self): 
        exit_action = QAction("Exit", self) 
        exit_action.triggered.connect(self.close) 
        self.menuBar().addAction(exit_action)
        
    def create_transaction_entry_tab(self):
        # Create the first tab for item entry and display
        self.tab1 = QWidget()
        self.tabs.addTab(self.tab1, "Item Entry")

        # Layout for the first tab
        self.tab1_layout = QGridLayout(self.tab1)

        # Create input fields for date, category, and amount
        self.date_input = QDateEdit(calendarPopup=True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setDisplayFormat('dd-MMM-yy')

        # Create a dropdown for categories
        self.category_input = QComboBox()
        category_list = [
            "Salary", "Rent", "Karate", "Broadband", "Phone",
            "Electricity", "Water", "Sam", "Food", "Eating out",
            "Sid", "Divs", "Car", "Remit", "Insurance", "Lotto",
            "Electronix", "Medical", "Laundry", "Trip", "General"
        ]
        self.category_input.addItems(category_list)

        self.amount_input = QLineEdit()

        # Create a submit button
        self.submit_button = QPushButton('Submit')
        self.submit_button.clicked.connect(self.add_transaction_from_input)

        # Add widgets to the left quadrant (0, 0)
        self.tab1_layout.setRowStretch(4, 1)
        self.tab1_layout.setVerticalSpacing(10)
        self.tab1_layout.addWidget(self.date_input, 0, 0)
        self.tab1_layout.addWidget(self.category_input, 1, 0)
        self.tab1_layout.addWidget(self.amount_input, 2, 0)
        self.tab1_layout.addWidget(self.submit_button, 3, 0)

        # Create a table to display transactions
        self.tab1_ledger_table = QTableWidget()
        self.tab1_ledger_table.setColumnCount(3)
        self.tab1_ledger_table.setHorizontalHeaderLabels(["Date", "Category", "Amount"])
        self.tab1_ledger_table.setRowCount(10)  # Set the number of rows you want to be visible

        # Set minimum row heights to ensure all rows are visible
        for row in range(10):
            self.tab1_ledger_table.setRowHeight(row, 20)  # Adjust the row height as needed

        # Add the table to the layout with appropriate row span to accommodate all rows
        self.tab1_layout.addWidget(self.tab1_ledger_table, 0, 1, 10, 1)  # Span 10 rows instead of 4

    def create_account_details_tab(self):
        # Create the second tab for accounting details
        self.tab2 = QWidget()
        self.tabs.addTab(self.tab2, "Accounting Details")

        # Layout for the second tab
        self.tab2_layout = QGridLayout(self.tab2)

        # Create UI components for account balances in the top right quadrant
        self.account_balance_widgets = {}
        self.main_accounts = ["Acoount1", "Acoount2", "Acoount3"]
        self.sub_accounts = {
            "Acoount1": ["Checking", "Savings", "Saver", "Kiwi Saver"],
            "Acoount2": ["Checking", "Savings", "Saver", "Kiwi Saver"],
            "Acoount3": ["Checking", "Savings"]
        }

        # Determine the unique sub-accounts to set as column headers
        unique_sub_accounts = set()
        for accounts in self.sub_accounts.values():
            unique_sub_accounts.update(accounts)
        unique_sub_accounts = sorted(list(unique_sub_accounts))

        # Create a QTableWidget
        self.table_widget = QTableWidget()
        self.table_widget.setRowCount(len(self.main_accounts))  # Set the number of rows
        self.table_widget.setColumnCount(len(unique_sub_accounts) + 1)  # +1 for the Total column
        self.table_widget.setHorizontalHeaderLabels(unique_sub_accounts + ["Total"])  # Set column headers

        # Initialize the table with row headers and line edits
        for row, main_account in enumerate(self.main_accounts):
            # Set row header (account name)
            self.table_widget.setVerticalHeaderItem(row, QTableWidgetItem(main_account))

            # Initialize line edits for sub-accounts
            for col, sub_account in enumerate(unique_sub_accounts):
                if sub_account in self.sub_accounts[main_account]:
                    sub_account_line_edit = QLineEdit()
                    self.account_balance_widgets[f"{main_account} {sub_account}"] = sub_account_line_edit
                    self.table_widget.setCellWidget(row, col, sub_account_line_edit)
                    sub_account_line_edit.textChanged.connect(self.compute_total)
                else:
                    # If the sub-account doesn't exist for this main account, add a disabled line edit
                    placeholder_line_edit = QLineEdit()
                    placeholder_line_edit.setDisabled(True)
                    self.table_widget.setCellWidget(row, col, placeholder_line_edit)

            # Initialize the total balance line edit
            total_balance_line_edit = QLineEdit("Total")
            total_balance_line_edit.setReadOnly(True)
            self.account_balance_widgets[f"{main_account} Total"] = total_balance_line_edit
            self.table_widget.setCellWidget(row, len(unique_sub_accounts), total_balance_line_edit)

        # Add the table widget to the layout
        self.tab2_layout.addWidget(self.table_widget, 0, 0, 1, -1)  # Span all columns

        # Add the update button below the table
        update_button = QPushButton("Update")
        self.tab2_layout.addWidget(update_button, 1, 0, 1, -1)  # Span all columns
        update_button.clicked.connect(self.save_accounting_details)

    def create_monthly_spending_tab(self):
        # Create the third tab for monthly accounts
        self.tab3 = QWidget()
        self.tabs.addTab(self.tab3, "Monthly Accounts")

        # Layout for the third tab
        self.tab3_layout = QGridLayout(self.tab3)
               
        # Create a table to display monthly spending
        self.monthly_spending_table = QTableWidget()
        self.monthly_spending_table.setColumnCount(2)  # For Category and Amount
        self.monthly_spending_table.setHorizontalHeaderLabels(["Category", "Amount"])

        # Create a dropdown for months
        self.month_input = QComboBox()
        
        # Referesh the monthly spending table
        self.refresh_monthly_spending_table()
        self.tab3_layout.addWidget(self.month_input, 0, 0)
        self.tab3_layout.addWidget(self.monthly_spending_table, 1, 0, 1, -1)  # Span all columns 
    
    def refresh_monthly_spending_table(self):
        #Get the list of months from the database
        self.month_list = self.get_month_list()
        self.month_input.clear()
        self.month_input.addItems(self.month_list)

        # Connect the month dropdown selection change to the update function if month_input is not empty
        if self.month_input.count() > 0:
            self.month_input.currentIndexChanged.connect(self.update_monthly_spending_table)
        
    def import_excel_tab(self):
        # Create the fourth tab for Excel file input
        self.tab4 = QWidget()
        self.tabs.addTab(self.tab4, "Excel Input")

        # Layout for the fourth tab
        self.tab4_layout = QGridLayout(self.tab4)

        # Create a button for selecting an Excel file
        self.select_file_button = QPushButton('Select Excel File')
        self.select_file_button.clicked.connect(self.open_file_dialog)
        self.tab4_layout.addWidget(self.select_file_button, 0, 0)
        # Create a button to clear transactions
        self.clear_transactions_button = QPushButton('Clear Transactions')
        self.clear_transactions_button.clicked.connect(self.clear_transactions)
        self.tab4_layout.addWidget(self.clear_transactions_button, 1, 0)

    def compute_total(self):
        # Iterate through each main account
        for main_account in self.main_accounts:
            total = 0
            # Sum the values of each sub-account line edit
            for sub_account in self.sub_accounts[main_account]:
                line_edit = self.account_balance_widgets[f"{main_account} {sub_account}"]
                value = line_edit.text()
                # Convert the value to a float and add to the total
                try:
                    total += float(value)
                except ValueError:
                    # If the value is not a number, ignore it
                    continue
            # Update the corresponding total balance line edit
            total_line_edit = self.account_balance_widgets[f"{main_account} Total"]
            total_line_edit.setText(str(total))

    def initialize_db(self):
        db_name = 'budget_tracker.db'
        db_path = os.path.join(os.path.dirname(__file__), db_name)

        # Check if the database file exists 
        if not os.path.isfile(db_path): 
            print(f"Database file {db_path} does not exist. Creating a new one.")
            
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
                  
        # Connect to the SQLite database
        self.db = QSqlDatabase.addDatabase('QSQLITE')
        self.db.setDatabaseName(db_path)

        # Open the connection
        if not self.db.open():
            print("Error: ", self.db.lastError().text())
            return False

        # Create a QSqlQuery object to execute SQL statements
        query = QSqlQuery()

        # Create a table if it doesn't exist
        query.exec_("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL
        )
        """)

        # Create a table for accounting details if it doesn't exist
        query.exec_("""
            CREATE TABLE IF NOT EXISTS accounting_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
                date TEXT NOT NULL,
                account_name TEXT NOT NULL,
                checking REAL,
                savings REAL,
                saver REAL,
                kiwi_saver REAL,
                total REAL NOT NULL
            )
        """)
        return True

    def load_latest_accounting_details(self):
        # Check if the database connection is open
        if not self.db.isOpen():
            if not self.db.open():
                print("Error: ", self.db.lastError().text())
                return

        query = QSqlQuery()

        # Fetch the latest accounting details for each main account
        for main_account in self.main_accounts:
            query.prepare("""
                SELECT checking, savings, saver, kiwi_saver, total
                FROM accounting_details
                WHERE account_name = :account_name
                ORDER BY date DESC
                LIMIT 1
            """)
            query.bindValue(":account_name", main_account)
            if query.exec_() and query.next():
                # Set the values of the line edits to the fetched data
                self.account_balance_widgets[f"{main_account} Checking"].setText(str(query.value(0)))
                self.account_balance_widgets[f"{main_account} Savings"].setText(str(query.value(1)))
                
                # Only set "Saver" and "Kiwi Saver" if they exist for the account
                if "Saver" in self.sub_accounts[main_account]:
                    self.account_balance_widgets[f"{main_account} Saver"].setText(str(query.value(2)))
                if "Kiwi Saver" in self.sub_accounts[main_account]:
                    self.account_balance_widgets[f"{main_account} Kiwi Saver"].setText(str(query.value(3)))
                
                # Set the total balance
                self.account_balance_widgets[f"{main_account} Total"].setText(str(query.value(4)))
            else:
                print(f"No accounting details found for {main_account} or failed to fetch data.")

    def save_accounting_details(self):
        query = QSqlQuery()
        for main_account in self.main_accounts:
            # Initialize a dictionary to hold the account data
            data = {
                'account_name': main_account,
                # Use Python's datetime.now() to get the current local date and time
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total': self.account_balance_widgets[f"{main_account} Total"].text()
            }

            # Iterate over each sub-account and safely get the text or set a default value
            for sub_account in ["Checking", "Savings", "Saver", "Kiwi Saver"]:
                line_edit = self.account_balance_widgets.get(f"{main_account} {sub_account}")
                data[sub_account.lower()] = line_edit.text() if line_edit is not None else '0'

            # Insert the data into the database
            query.prepare("""
                INSERT INTO accounting_details (account_name, date, checking, savings, saver, kiwi_saver, total)
                VALUES (:account_name, :date, :checking, :savings, :saver, :kiwi_saver, :total)
            """)
            # Bind the values for the INSERT
            for key, value in data.items():
                query.bindValue(f":{key}", value)
            if not query.exec_():
                print("Update error: ", query.lastError().text())
            else:
                print(f"Accounting details for {main_account} updated successfully.")

    def refresh_ledger_table(self):
        # Clear the existing table content
        self.tab1_ledger_table.setRowCount(0)

        # Execute a query to fetch the latest 10 data entries, ordered by id descending
        query = QSqlQuery("SELECT date, category, amount FROM transactions ORDER BY id DESC LIMIT 10")

        # Populate the table with the data
        while query.next():
            row_position = self.tab1_ledger_table.rowCount()
            self.tab1_ledger_table.insertRow(row_position)
            self.tab1_ledger_table.setItem(row_position, 0, QTableWidgetItem(query.value(0)))
            self.tab1_ledger_table.setItem(row_position, 1, QTableWidgetItem(query.value(1)))
            self.tab1_ledger_table.setItem(row_position, 2, QTableWidgetItem(str(f"{query.value(2):.2f}")))

        # Reverse the order of the rows to show the most recent at the top
        for row in range(self.tab1_ledger_table.rowCount() // 2):
            for col in range(self.tab1_ledger_table.columnCount()):
                top_item = self.tab1_ledger_table.takeItem(row, col)
                bottom_row = self.tab1_ledger_table.rowCount() - row - 1
                bottom_item = self.tab1_ledger_table.takeItem(bottom_row, col)
                self.tab1_ledger_table.setItem(row, col, bottom_item)
                self.tab1_ledger_table.setItem(bottom_row, col, top_item)

        # Optionally, adjust column widths for better readability
        self.tab1_ledger_table.resizeColumnsToContents()

    def add_transaction_from_input(self):
        # Get input values
        date = self.date_input.date().toString('dd-MMM-yy')
        expenditure_type = self.category_input.currentText()
        amount = self.amount_input.text()

        # Add transaction to the table
        self.add_transaction(date, expenditure_type, amount)

        # Clear input fields
        self.amount_input.clear()

        # Refresh the table view to show the latest transactions
        self.refresh_ledger_table()

    def add_transaction(self, date, category, amount):
        # Create a QSqlQuery object
        query = QSqlQuery()

        # Prepare the insert SQL statement
        query.prepare("INSERT INTO transactions (date, category, amount) VALUES (?, ?, ?)")

        # Bind the values to the placeholders
        query.addBindValue(date)
        query.addBindValue(category)
        query.addBindValue(amount)

        # Execute the query
        if not query.exec_():
            print("Error: ", query.lastError().text())

    # Add the new methods for the third tab functionality here
    def get_month_list(self):

        if not self.db.isOpen():
            if not self.db.open():
                print("Error: ", self.db.lastError().text())
                return []

        month_list = []
        query = QSqlQuery(self.db)

        # Execute a simple query to fetch all dates
        if query.exec_("SELECT DISTINCT date FROM transactions"):
            while query.next():
                # Fetch the date as a string from the database
                date_str = query.value(0)
                # Convert the date string to a datetime object
                try:
                    date_obj = datetime.strptime(date_str, '%d-%b-%y')
                    # Format the date as 'YYYY-MM' and add to the list if not already present
                    month_year_str = date_obj.strftime('%Y-%m')
                    if month_year_str not in month_list:
                        month_list.append(month_year_str)
                except ValueError:
                    print(f"Date conversion error: {date_str}")

        else:
            print("Query failed: ", query.lastError().text())
        
        # At the end of your get_month_list function, before returning the list
        formatted_month_list = []
        for month_year_str in month_list:
            # Convert 'YYYY-MM' to 'MMM-YYYY'
            date_obj = datetime.strptime(month_year_str, '%Y-%m')
            formatted_month_list.append(date_obj.strftime('%b-%Y'))

        return formatted_month_list

    def update_monthly_spending_table(self):
        selected_month_year = self.month_input.currentText()

        try:
            # Convert the selected month-year string to datetime object
            selected_date = datetime.strptime(selected_month_year, '%b-%Y')
            # Format the selected date to match the database format 'MMM-YY'
            formatted_selected_date = selected_date.strftime('%b-%y')

            # Prepare the SQL query to sum up spending by category for the selected month
            query_str = f"""
                SELECT category, SUM(amount) 
                FROM transactions 
                WHERE date LIKE '%{formatted_selected_date}' 
                GROUP BY category
            """
            query = QSqlQuery(self.db)
            if query.exec_(query_str):
                # Clear the table before inserting new data
                self.monthly_spending_table.setRowCount(0)
                row = 0
                while query.next():
                    # Insert new rows into the table for each category
                    self.monthly_spending_table.insertRow(row)
                    # Category
                    self.monthly_spending_table.setItem(row, 0, QTableWidgetItem(query.value(0)))
                    # Summed amount
                    self.monthly_spending_table.setItem(
                        row, 1, QTableWidgetItem(f"{query.value(1):.2f}"))
                    row += 1
            else:
                error = query.lastError().text()
                # Handle any errors appropriately
        except ValueError as e:
            if "time data '' does not match format '%b-%Y'" in str(e):
                self.monthly_spending_table.setRowCount(0)
            else:
                # Handle other failures in table handling
                print(f"Updating monthly spending table failed: {e}")
            
    def read_and_update_database(self, file_path):
        # Read the Excel file into a pandas DataFrame
        df = pd.read_excel(file_path)
        
        # Replace NaN values with 0 for expenditures not made in certain months
        df.fillna(0, inplace=True)
        
        # Check if the database connection is open
        if not self.db.isOpen():
            if not self.db.open():
                print("Error: ", self.db.lastError().text())
                return []
        
        # Loop through each month's column in DataFrame starting from index 1 since index 0 is categories
        for month_col in df.columns[1:]:
            # Extract the month and year from the column name
            month_year = datetime.strptime(month_col, '%b-%y')
            # Assume the first day of the month for the date
            date_col = month_year.strftime('%d-%b-%y')

            # Create a temporary DataFrame with 'Category', 'Amount', and 'Date' columns
            temp_df = pd.DataFrame({
                'category': df.iloc[:, 0],
                'amount': df[month_col].abs(),  # Convert negative amounts to positive
                'date': date_col
            })
            
            # Add each transaction to the database 
            for index, row in temp_df.iterrows(): 
                self.add_transaction(row['date'], row['category'], row['amount'])

        # Show a message box indicating the import is complete
        QMessageBox.information(self, "Import Complete", "The spreadsheet has been successfully imported.")
        
        # Refresh the table view to show the latest transactions
        self.refresh_ledger_table()
        # Refresh the monthly spending table using latest import
        self.refresh_monthly_spending_table()

    def open_file_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Excel File", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
        if file_name:
            # Call the function to handle the file and update the database
            self.read_and_update_database(file_name)

    def clear_transactions(self):
        query = QSqlQuery()
        if query.exec_("DELETE FROM transactions"):
            # Show a message box indicating transactions have been cleared
            QMessageBox.information(self, "Transactions Cleared", "Transactions in database has been cleared.")
            self.refresh_ledger_table()  # Refresh the table view to reflect the changes
            self.refresh_monthly_spending_table()
        else:
            print("Error: ", query.lastError().text())

    def closeEvent(self, event): 
        # Close the database connection before exiting 
        if hasattr(self, 'db') and self.db.isOpen(): 
            self.db.close() 
            print("Database connection closed.")
            
        event.accept()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BudgetTracker()
    window.show()
    sys.exit(app.exec_())
