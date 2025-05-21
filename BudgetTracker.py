import sys
import os
from PyQt5.QtSql import QSqlDatabase, QSqlQuery
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QMessageBox, QWidget, QGridLayout,
    QDateEdit, QComboBox, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QAction, QFileDialog
)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QDoubleValidator
import pandas as pd

class BudgetTracker(QMainWindow):
    """Main window for the Budget Tracker application."""

    CATEGORY_LIST = [
        "Salary", "Rent", "Karate", "Broadband", "Phone",
        "Electricity", "Water", "Sam", "Food", "Eating out",
        "Sid", "Divs", "Car", "Remit", "Insurance", "Lotto",
        "Electronix", "Medical", "Laundry", "Trip", "General"
    ]
    MAIN_ACCOUNTS = ["Account1", "Account2", "Account3"]
    SUB_ACCOUNTS = {
        "Account1": ["Checking", "Savings", "Saver", "Kiwi Saver"],
        "Account2": ["Checking", "Savings", "Saver", "Kiwi Saver"],
        "Account3": ["Checking", "Savings"]
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Budget Tracker 2.0")
        self.setGeometry(100, 100, 800, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.create_transaction_entry_tab()
        self.create_account_details_tab()

        if not self.initialize_db():
            print("Failed to initialize the databases")
            return

        self.load_latest_accounting_details()
        self.create_monthly_spending_tab()
        self.refresh_ledger_table()
        self.import_excel_tab()
        self.setup_menu()

    def setup_menu(self):
        """Setup the application menu."""
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        self.menuBar().addAction(exit_action)

    def create_transaction_entry_tab(self):
        """Create the tab for entering and displaying transactions."""
        self.tab1 = QWidget()
        self.tabs.addTab(self.tab1, "Item Entry")
        self.tab1_layout = QGridLayout(self.tab1)

        self.date_input = QDateEdit(calendarPopup=True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setDisplayFormat('dd-MMM-yy')

        self.category_input = QComboBox()
        self.category_input.addItems(self.CATEGORY_LIST)

        self.amount_input = QLineEdit()
        self.amount_input.setValidator(QDoubleValidator(0.00, 1000000.00, 2))
        self.amount_input.returnPressed.connect(self.add_transaction_from_input)

        self.submit_button = QPushButton('Submit')
        self.submit_button.clicked.connect(self.add_transaction_from_input)

        self.tab1_layout.setRowStretch(4, 1)
        self.tab1_layout.setVerticalSpacing(10)
        self.tab1_layout.addWidget(self.date_input, 0, 0)
        self.tab1_layout.addWidget(self.category_input, 1, 0)
        self.tab1_layout.addWidget(self.amount_input, 2, 0)
        self.tab1_layout.addWidget(self.submit_button, 3, 0)

        self.tab1_ledger_table = QTableWidget()
        self.tab1_ledger_table.setColumnCount(3)
        self.tab1_ledger_table.setHorizontalHeaderLabels(["Date", "Category", "Amount"])
        self.tab1_ledger_table.setRowCount(10)
        for row in range(10):
            self.tab1_ledger_table.setRowHeight(row, 20)
        self.tab1_layout.addWidget(self.tab1_ledger_table, 0, 1, 10, 1)

    def create_account_details_tab(self):
        """Create the tab for managing account balances."""
        self.tab2 = QWidget()
        self.tabs.addTab(self.tab2, "Accounting Details")
        self.tab2_layout = QGridLayout(self.tab2)

        self.account_balance_widgets = {}
        unique_sub_accounts = sorted({sub for subs in self.SUB_ACCOUNTS.values() for sub in subs})

        self.table_widget = QTableWidget()
        self.table_widget.setRowCount(len(self.MAIN_ACCOUNTS))
        self.table_widget.setColumnCount(len(unique_sub_accounts) + 1)
        self.table_widget.setHorizontalHeaderLabels(unique_sub_accounts + ["Total"])

        for row, main_account in enumerate(self.MAIN_ACCOUNTS):
            self.table_widget.setVerticalHeaderItem(row, QTableWidgetItem(main_account))
            for col, sub_account in enumerate(unique_sub_accounts):
                if sub_account in self.SUB_ACCOUNTS[main_account]:
                    sub_account_line_edit = QLineEdit()
                    self.account_balance_widgets[f"{main_account} {sub_account}"] = sub_account_line_edit
                    self.table_widget.setCellWidget(row, col, sub_account_line_edit)
                    sub_account_line_edit.textChanged.connect(self.compute_total)
                    sub_account_line_edit.returnPressed.connect(self.save_accounting_details)
                else:
                    placeholder_line_edit = QLineEdit()
                    placeholder_line_edit.setDisabled(True)
                    self.table_widget.setCellWidget(row, col, placeholder_line_edit)
            total_balance_line_edit = QLineEdit("Total")
            total_balance_line_edit.setReadOnly(True)
            self.account_balance_widgets[f"{main_account} Total"] = total_balance_line_edit
            self.table_widget.setCellWidget(row, len(unique_sub_accounts), total_balance_line_edit)

        self.tab2_layout.addWidget(self.table_widget, 0, 0, 1, -1)
        update_button = QPushButton("Update")
        self.tab2_layout.addWidget(update_button, 1, 0, 1, -1)
        update_button.clicked.connect(self.save_accounting_details)

    def create_monthly_spending_tab(self):
        """Create the tab for monthly spending summary."""
        self.tab3 = QWidget()
        self.tabs.addTab(self.tab3, "Monthly Accounts")
        self.tab3_layout = QGridLayout(self.tab3)

        self.monthly_spending_table = QTableWidget()
        self.monthly_spending_table.setColumnCount(2)
        self.monthly_spending_table.setHorizontalHeaderLabels(["Category", "Amount"])

        self.month_input = QComboBox()
        self.month_input.currentIndexChanged.connect(self.update_monthly_spending_table)

        self.totals_box = QTableWidget()
        self.totals_box.setColumnCount(2)
        self.totals_box.setRowCount(3)
        self.totals_box.setHorizontalHeaderLabels(["Summary", "Amount"])
        self.totals_box.setItem(0, 0, QTableWidgetItem("Salary"))
        self.totals_box.setItem(1, 0, QTableWidgetItem("Total Expenses"))
        self.totals_box.setItem(2, 0, QTableWidgetItem("Total Profit/Loss"))
        self.totals_box.setFixedWidth(300)
        self.totals_box.setEditTriggers(QTableWidget.NoEditTriggers)

        self.tab3_layout.addWidget(self.month_input, 0, 0, 1, 2)
        self.tab3_layout.addWidget(self.monthly_spending_table, 1, 0)
        self.tab3_layout.addWidget(self.totals_box, 1, 1)
        self.tab3_layout.setColumnStretch(0, 2)
        self.tab3_layout.setColumnStretch(1, 1)
        self.refresh_monthly_spending_table()

    def refresh_monthly_spending_table(self):
        """Refresh the list of months in the dropdown."""
        self.month_list = self.get_month_list()
        self.month_input.clear()
        self.month_input.addItems(self.month_list)

    def import_excel_tab(self):
        """Create the tab for importing Excel files."""
        self.tab4 = QWidget()
        self.tabs.addTab(self.tab4, "Excel Input")
        self.tab4_layout = QGridLayout(self.tab4)

        self.select_file_button = QPushButton('Select Excel File')
        self.select_file_button.clicked.connect(self.open_file_dialog)
        self.tab4_layout.addWidget(self.select_file_button, 0, 0)

        self.clear_transactions_button = QPushButton('Clear Transactions')
        self.clear_transactions_button.clicked.connect(self.clear_transactions)
        self.tab4_layout.addWidget(self.clear_transactions_button, 1, 0)

    def compute_total(self):
        """Compute and update the total for each main account."""
        for main_account in self.MAIN_ACCOUNTS:
            total = 0
            for sub_account in self.SUB_ACCOUNTS[main_account]:
                line_edit = self.account_balance_widgets[f"{main_account} {sub_account}"]
                value = line_edit.text()
                try:
                    total += float(value)
                except ValueError:
                    continue
            total_line_edit = self.account_balance_widgets[f"{main_account} Total"]
            total_line_edit.setText(str(total))

    def initialize_db(self):
        """Initialize the SQLite database and tables."""
        db_name = 'budget_tracker.db'
        db_path = os.path.join(os.path.dirname(__file__), db_name)
        if not os.path.isfile(db_path):
            print(f"Database file {db_path} does not exist. Creating a new one.")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = QSqlDatabase.addDatabase('QSQLITE')
        self.db.setDatabaseName(db_path)
        if not self.db.open():
            print("Error: ", self.db.lastError().text())
            return False
        query = QSqlQuery()
        query.exec_("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL
            )
        """)
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
        """Load the latest account balances from the database."""
        if not self.db.isOpen():
            if not self.db.open():
                print("Error: ", self.db.lastError().text())
                return
        query = QSqlQuery()
        for main_account in self.MAIN_ACCOUNTS:
            query.prepare("""
                SELECT checking, savings, saver, kiwi_saver, total
                FROM accounting_details
                WHERE account_name = :account_name
                ORDER BY date DESC
                LIMIT 1
            """)
            query.bindValue(":account_name", main_account)
            if query.exec_() and query.next():
                self.account_balance_widgets[f"{main_account} Checking"].setText(str(query.value(0)))
                self.account_balance_widgets[f"{main_account} Savings"].setText(str(query.value(1)))
                if "Saver" in self.SUB_ACCOUNTS[main_account]:
                    self.account_balance_widgets[f"{main_account} Saver"].setText(str(query.value(2)))
                if "Kiwi Saver" in self.SUB_ACCOUNTS[main_account]:
                    self.account_balance_widgets[f"{main_account} Kiwi Saver"].setText(str(query.value(3)))
                self.account_balance_widgets[f"{main_account} Total"].setText(str(query.value(4)))
            else:
                print(f"No accounting details found for {main_account} or failed to fetch data.")

    def save_accounting_details(self):
        """Save the current account balances to the database."""
        query = QSqlQuery()
        for main_account in self.MAIN_ACCOUNTS:
            data = {
                'account_name': main_account,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total': self.account_balance_widgets[f"{main_account} Total"].text()
            }
            for sub_account in ["Checking", "Savings", "Saver", "Kiwi Saver"]:
                line_edit = self.account_balance_widgets.get(f"{main_account} {sub_account}")
                data[sub_account.lower()] = line_edit.text() if line_edit is not None else '0'
            query.prepare("""
                INSERT INTO accounting_details (account_name, date, checking, savings, saver, kiwi_saver, total)
                VALUES (:account_name, :date, :checking, :savings, :saver, :kiwi_saver, :total)
            """)
            for key, value in data.items():
                query.bindValue(f":{key}", value)
            if not query.exec_():
                print("Update error: ", query.lastError().text())
            else:
                print(f"Accounting details for {main_account} updated successfully.")

    def refresh_ledger_table(self):
        """Refresh the transaction ledger table."""
        self.tab1_ledger_table.setRowCount(0)
        query = QSqlQuery("SELECT date, category, amount FROM transactions ORDER BY id DESC LIMIT 10")
        while query.next():
            row_position = self.tab1_ledger_table.rowCount()
            self.tab1_ledger_table.insertRow(row_position)
            self.tab1_ledger_table.setItem(row_position, 0, QTableWidgetItem(query.value(0)))
            self.tab1_ledger_table.setItem(row_position, 1, QTableWidgetItem(query.value(1)))
            try:
                amount = float(query.value(2))
                formatted_amount = f"{amount:.2f}"
            except (ValueError, TypeError):
                formatted_amount = str(query.value(2))
            self.tab1_ledger_table.setItem(row_position, 2, QTableWidgetItem(formatted_amount))
        for row in range(self.tab1_ledger_table.rowCount() // 2):
            for col in range(self.tab1_ledger_table.columnCount()):
                top_item = self.tab1_ledger_table.takeItem(row, col)
                bottom_row = self.tab1_ledger_table.rowCount() - row - 1
                bottom_item = self.tab1_ledger_table.takeItem(bottom_row, col)
                self.tab1_ledger_table.setItem(row, col, bottom_item)
                self.tab1_ledger_table.setItem(bottom_row, col, top_item)
        self.tab1_ledger_table.resizeColumnsToContents()

    def add_transaction_from_input(self):
        """Add a transaction from the input fields."""
        date = self.date_input.date().toString('dd-MMM-yy')
        expenditure_type = self.category_input.currentText()
        amount = self.amount_input.text()
        try:
            float(amount)
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please enter a valid number for the amount.\nExample: 123.45",
                QMessageBox.Ok
            )
            self.amount_input.clear()
            return
        self.add_transaction(date, expenditure_type, amount)
        self.amount_input.clear()
        self.refresh_ledger_table()

    def add_transaction(self, date, category, amount):
        """Insert a transaction into the database."""
        query = QSqlQuery()
        query.prepare("INSERT INTO transactions (date, category, amount) VALUES (?, ?, ?)")
        query.addBindValue(date)
        query.addBindValue(category)
        query.addBindValue(amount)
        if not query.exec_():
            print("Error: ", query.lastError().text())

    def get_month_list(self):
        """Get a list of months with transactions."""
        if not self.db.isOpen():
            if not self.db.open():
                print("Error: ", self.db.lastError().text())
                return []
        month_list = []
        query = QSqlQuery(self.db)
        if query.exec_("SELECT DISTINCT date FROM transactions"):
            while query.next():
                date_str = query.value(0)
                try:
                    date_obj = datetime.strptime(date_str, '%d-%b-%y')
                    month_year_str = date_obj.strftime('%Y-%m')
                    if month_year_str not in month_list:
                        month_list.append(month_year_str)
                except ValueError:
                    print(f"Date conversion error: {date_str}")
        else:
            print("Query failed: ", query.lastError().text())
        formatted_month_list = []
        for month_year_str in month_list:
            date_obj = datetime.strptime(month_year_str, '%Y-%m')
            formatted_month_list.append(date_obj.strftime('%b-%Y'))
        return formatted_month_list

    def update_monthly_spending_table(self):
        """Update the monthly spending summary for the selected month."""
        selected_month_year = self.month_input.currentText()
        try:
            selected_date = datetime.strptime(selected_month_year, '%b-%Y')
            formatted_selected_date = selected_date.strftime('%b-%y')
            query_str = """
                SELECT category, SUM(amount) 
                FROM transactions 
                WHERE date LIKE ?
                GROUP BY category
            """
            query = QSqlQuery(self.db)
            query.prepare(query_str)
            query.addBindValue(f'%{formatted_selected_date}')
            if query.exec_():
                self.monthly_spending_table.setRowCount(0)
                row = 0
                total_expenses = 0
                salary = 0
                while query.next():
                    category = query.value(0)
                    amount = float(query.value(1))
                    if category == "Salary":
                        salary = amount
                        self.monthly_spending_table.insertRow(row)
                        self.monthly_spending_table.setItem(row, 0, QTableWidgetItem(category))
                        amount_item = QTableWidgetItem(f"{amount:.2f}")
                        amount_item.setForeground(Qt.darkGreen)
                    else:
                        total_expenses += amount
                        self.monthly_spending_table.insertRow(row)
                        self.monthly_spending_table.setItem(row, 0, QTableWidgetItem(category))
                        amount_item = QTableWidgetItem(f"-{amount:.2f}")
                        amount_item.setForeground(Qt.red)
                    self.monthly_spending_table.setItem(row, 1, amount_item)
                    row += 1
                salary_item = QTableWidgetItem(f"{salary:.2f}")
                salary_item.setForeground(Qt.darkGreen)
                self.totals_box.setItem(0, 1, salary_item)
                expenses_item = QTableWidgetItem(f"-{total_expenses:.2f}")
                expenses_item.setForeground(Qt.red)
                self.totals_box.setItem(1, 1, expenses_item)
                net_amount = salary - total_expenses
                net_item = QTableWidgetItem(f"{net_amount:.2f}")
                net_item.setForeground(Qt.darkGreen if net_amount >= 0 else Qt.red)
                self.totals_box.setItem(2, 1, net_item)
            else:
                QMessageBox.warning(self, "Query Error", query.lastError().text())
        except ValueError as e:
            if "time data '' does not match format '%b-%Y'" in str(e):
                self.monthly_spending_table.setRowCount(0)
                self.totals_box.setItem(0, 1, QTableWidgetItem("0.00"))
                self.totals_box.setItem(1, 1, QTableWidgetItem("0.00"))
                self.totals_box.setItem(2, 1, QTableWidgetItem("0.00"))
            else:
                QMessageBox.warning(self, "Error", str(e))

    def read_and_update_database(self, file_path):
        """Read an Excel file and update the database with its contents."""
        df = pd.read_excel(file_path)
        df.fillna(0, inplace=True)
        if not self.db.isOpen():
            if not self.db.open():
                print("Error: ", self.db.lastError().text())
                return []
        for month_col in df.columns[1:]:
            month_year = datetime.strptime(month_col, '%b-%y')
            date_col = month_year.strftime('%d-%b-%y')
            temp_df = pd.DataFrame({
                'category': df.iloc[:, 0],
                'amount': df[month_col].abs(),
                'date': date_col
            })
            for _, row in temp_df.iterrows():
                self.add_transaction(row['date'], row['category'], row['amount'])
        QMessageBox.information(self, "Import Complete", "The spreadsheet has been successfully imported.")
        self.refresh_ledger_table()
        self.refresh_monthly_spending_table()

    def open_file_dialog(self):
        """Open a file dialog to select an Excel file."""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Excel File", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
        if file_name:
            self.read_and_update_database(file_name)

    def clear_transactions(self):
        """Clear all transactions from the database."""
        query = QSqlQuery()
        if query.exec_("DELETE FROM transactions"):
            QMessageBox.information(self, "Transactions Cleared", "Transactions in database has been cleared.")
            self.refresh_ledger_table()
            self.refresh_monthly_spending_table()
        else:
            print("Error: ", query.lastError().text())

    def closeEvent(self, event):
        """Handle the close event to ensure the database is closed."""
        if hasattr(self, 'db') and self.db.isOpen():
            self.db.close()
            print("Database connection closed.")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BudgetTracker()
    window.show()
    sys.exit(app.exec_())
