# -*- coding: utf-8 -*-
import subprocess
import tkinter as tk
from pathlib import Path

from core.categorize import categorize_new_transactions, train_classifier
from core.import_statements import import_all_statements
from core.missing import missing
from core.plots import plot_balances, plot_categories

# Initialize the GUI class
root = tk.Tk()


def donothing():
    """
    Example function
    """
    filewin = tk.Toplevel(root)
    button = tk.Button(filewin, text="Do nothing button")
    button.pack()


def open_db():
    filename = str(Path("") / "pyguibank.db")
    subprocess.run(["open", filename], check=True)


def main_menu():
    # Create top level menu bar
    menubar = tk.Menu(root)

    # Create File menu
    filemenu = tk.Menu(menubar, tearoff=0)
    filemenu.add_command(label="New", command=donothing)
    filemenu.add_command(label="Open", command=donothing)
    filemenu.add_command(label="Save", command=donothing)
    filemenu.add_command(label="Save as...", command=donothing)
    filemenu.add_command(label="Close", command=donothing)
    filemenu.add_separator()
    filemenu.add_command(label="Exit", command=root.quit)
    menubar.add_cascade(label="File", menu=filemenu)

    # Create Edit menu
    editmenu = tk.Menu(menubar, tearoff=0)
    editmenu.add_command(label="Undo", command=donothing)
    editmenu.add_separator()
    editmenu.add_command(label="Cut", command=donothing)
    editmenu.add_command(label="Copy", command=donothing)
    editmenu.add_command(label="Paste", command=donothing)
    editmenu.add_command(label="Delete", command=donothing)
    editmenu.add_command(label="Select All", command=donothing)
    menubar.add_cascade(label="Edit", menu=editmenu)

    # Create Help menu
    helpmenu = tk.Menu(menubar, tearoff=0)
    helpmenu.add_command(label="Help Index", command=donothing)
    helpmenu.add_command(label="About...", command=donothing)
    menubar.add_cascade(label="Help", menu=helpmenu)

    # Add menubar to root configuration
    root.config(menu=menubar)


def main_window():
    """
    Main GUI window button initialization
    """
    button_frame = tk.Frame(root)
    button_frame.pack()

    button_opendb = tk.Button(button_frame, text="Open Database", command=open_db)
    button_opendb.pack()

    button_statements = tk.Button(
        button_frame, text="Show Statement Matrix", command=missing
    )
    button_statements.pack()

    button_import = tk.Button(
        button_frame, text="Import New Statements", command=import_all_statements
    )
    button_import.pack()

    button_categorize = tk.Button(
        button_frame,
        text="Categorize New Transactions",
        command=categorize_new_transactions,
    )
    button_categorize.pack()

    button_train = tk.Button(
        button_frame, text="Retrain Classifier Model", command=train_classifier
    )
    button_train.pack()

    button_plot_balances = tk.Button(
        button_frame, text="Plot Balances", command=plot_balances
    )
    button_plot_balances.pack()

    button_plot_categories = tk.Button(
        button_frame, text="Plot Categories", command=plot_categories
    )
    button_plot_categories.pack()


if __name__ == "__main__":
    # Set up the GUI
    main_menu()
    main_window()

    # Start the GUI
    root.title("PyGuiBank")
    root.geometry("640x480")
    root.mainloop()
