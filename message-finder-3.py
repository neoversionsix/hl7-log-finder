"""
HL7 Log Finder GUI with Calendar Date Pickers

Features:
- Calendar-based date selection for "Date Greater Than" and "Date Less Than".
- Comma-separated multiple search terms (e.g. "THUY, ABC123, TestString").
- Finds HL7 messages in files within a date range (based on folder names).
- Writes matching messages to a timestamped .md file in the 'output' subfolder.
- Shows errors in a message box if something goes wrong (e.g., network or file writing).

Dependencies:
- tkcalendar (pip install tkcalendar)
"""

import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry  # Provides a calendar-based date selection widget

def date_to_YYYYMMDD(date_obj):
    """
    Converts a Python date object (from DateEntry) into a YYYYMMDD string.

    Example:
        datetime.date(2025, 1, 15) -> '20250115'
    """
    return date_obj.strftime('%Y%m%d')

def run_search():
    """
    Triggered when the user clicks the "Run Search" button.
    1. Gathers dates from DateEntry widgets and converts them to strings (YYYYMMDD).
    2. Gathers comma-separated search terms from the text field.
    3. Validates user input and date ranges.
    4. Searches HL7 log files in the specified network share, filtering by date and terms.
    5. Writes matching messages to a file in the 'output' folder, or shows an error if needed.
    """

    # -------------------------------------------------------------------------
    # 1. Get user inputs from the GUI
    # -------------------------------------------------------------------------
    # Convert the selected calendar dates to YYYYMMDD format for numeric comparison
    date_greater_str = date_to_YYYYMMDD(date_greater_entry.get_date())
    date_less_str    = date_to_YYYYMMDD(date_less_entry.get_date())

    # Get the user-entered comma-separated search terms
    search_terms_str = entry_search_terms.get().strip()

    # If no search terms are entered, show an error and stop
    if not search_terms_str:
        messagebox.showerror("Input Error", "Please enter at least one search term.")
        return

    # Convert the comma-separated string into a list of terms, stripping whitespace
    terms = [term.strip() for term in search_terms_str.split(',') if term.strip()]

    # -------------------------------------------------------------------------
    # 2. Parse and validate date strings
    # -------------------------------------------------------------------------
    # Convert them to integers for numeric comparison (YYYYMMDD -> int)
    try:
        date_greater_than = int(date_greater_str)
        date_less_than    = int(date_less_str)
    except ValueError:
        # If conversion fails (should not happen with DateEntry, but just in case)
        messagebox.showerror("Input Error", "Error converting dates. Please re-check your selections.")
        return

    # We want "date_greater_than" to be less than "date_less_than"
    if date_greater_than >= date_less_than:
        messagebox.showerror("Input Error", "'Date Greater Than' must be strictly less than 'Date Less Than'.")
        return

    # -------------------------------------------------------------------------
    # 3. Prepare output filename and path
    # -------------------------------------------------------------------------
    # Create a timestamp for the filename, e.g., "2025-01-15T12-33-49_123456"
    timestamp_str = datetime.datetime.now().isoformat().replace(':', '-').replace('.', '_')
    filename = f'OUTPUT-{timestamp_str}.md'

    # Determine where the script is running from
    # __file__ works if this code is in a .py file; otherwise, fallback to os.getcwd()
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()

    # Create or verify there's an 'output' subfolder next to the script
    output_folder = os.path.join(script_dir, 'output')
    os.makedirs(output_folder, exist_ok=True)

    # Full path to the output file
    output_file_path = os.path.join(output_folder, filename)

    # Initialize a list to store the matched results
    output_lines = ['# HL7 Search Results\n']

    # -------------------------------------------------------------------------
    # 4. Search files in the network share
    # -------------------------------------------------------------------------
    # Example UNC path (change to the correct share/folder as needed):
    network_share_path = r'\\whsrhaparch1\RhapsodyHL7FileLogs_Prod\MasterLog'

    # Try to list the top-level folder
    try:
        files_or_folders = os.listdir(network_share_path)
    except Exception as e:
        # If this fails, it's likely a permissions or connectivity error
        messagebox.showerror("Network Error", f"Could not list directory:\n{str(e)}")
        return

    # Filter out anything ending with '.zip', as we only want folders
    folders = [item for item in files_or_folders if not item.endswith('zip')]

    # Extract folders that match our date criteria from their first 8 chars
    filtered_folders = [
        folder for folder in folders
        if len(folder) >= 8 and folder[:8].isdigit()
           and date_greater_than < int(folder[:8]) < date_less_than
    ]

    # Optional: Print the search process to console for debugging
    print('# HL7 Search Results (Console Output)')

    # Loop over each filtered folder
    for folder_name in filtered_folders:
        folder_path = os.path.join(network_share_path, folder_name)

        # Try listing files in the folder
        try:
            files_in_folder = os.listdir(folder_path)
        except Exception as e:
            print(f"Skipping folder '{folder_name}' due to error: {e}")
            continue

        # Loop over each file in the folder
        for file_name in files_in_folder:
            file_path = os.path.join(folder_path, file_name)

            # Try opening the file in read mode
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as infile:
                    read_data = infile.read()
            except Exception as e:
                print(f"Skipping file '{file_path}' due to error: {e}")
                continue

            # HL7 messages are separated by '======'
            hl7_list = read_data.split('======')

            # For each HL7 message, check if all terms are present
            for hl7_message in hl7_list:
                # If you want ANY term to match, change "all" -> "any"
                if all(term in hl7_message for term in terms):
                    # Print to console (optional)
                    print(f'## {file_path}')
                    print(hl7_message)

                    # Add the message to the output buffer
                    output_lines.append(f'## {file_path}\n')
                    output_lines.append(f'{hl7_message}\n')
                    print('Added HL7 message to output')

    # -------------------------------------------------------------------------
    # 5. Write the results to the output file
    # -------------------------------------------------------------------------
    try:
        with open(output_file_path, 'w', encoding='utf-8') as outfile:
            outfile.writelines(output_lines)
        # Notify the user of success
        messagebox.showinfo("Success", f"Search complete!\n\nResults saved to:\n{output_file_path}")
        print(f"Successfully wrote output to {output_file_path}")
    except Exception as e:
        # If writing fails, show error and print everything to console
        msg = f"Error writing to file: {e}\nPrinting results to console instead."
        messagebox.showerror("File Write Error", msg)
        print(msg)
        print(''.join(output_lines))

# -----------------------------------------------------------------------------
# GUI Setup
# -----------------------------------------------------------------------------
root = tk.Tk()
root.title("HL7 Log Finder")
root.resizable(False, False)  # Window won't be resizable

# Main frame to hold all controls, with some padding
frame = ttk.Frame(root, padding="10 10 10 10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E))

# -----------------------------------------------------------------------------
# 1. Date Greater Than (DateEntry)
# -----------------------------------------------------------------------------
ttk.Label(frame, text="Date Greater Than:").grid(row=0, column=0, sticky=tk.W)

# DateEntry widget uses the system calendar by default
date_greater_entry = DateEntry(frame, width=12, date_pattern="yyyy/mm/dd")
date_greater_entry.grid(row=0, column=1, padx=5, pady=5)

# Pre-fill with an example date if you like:
# date_greater_entry.set_date(datetime.date(2024, 12, 5))

# -----------------------------------------------------------------------------
# 2. Date Less Than (DateEntry)
# -----------------------------------------------------------------------------
ttk.Label(frame, text="Date Less Than:").grid(row=1, column=0, sticky=tk.W)

date_less_entry = DateEntry(frame, width=12, date_pattern="yyyy/mm/dd")
date_less_entry.grid(row=1, column=1, padx=5, pady=5)

# Pre-fill with an example date if you like:
# date_less_entry.set_date(datetime.date(2024, 12, 6))

# -----------------------------------------------------------------------------
# 3. Search Terms (comma-separated)
# -----------------------------------------------------------------------------
ttk.Label(frame, text="Search Terms (comma-separated):").grid(row=2, column=0, sticky=tk.W)

entry_search_terms = ttk.Entry(frame, width=30)
entry_search_terms.grid(row=2, column=1, padx=5, pady=5)

# Example placeholder
entry_search_terms.insert(0, "THUY, ABC123")

# -----------------------------------------------------------------------------
# 4. Run Search Button
# -----------------------------------------------------------------------------
btn_run = ttk.Button(frame, text="Run Search", command=run_search)
btn_run.grid(row=3, column=0, columnspan=2, pady=10)

# -----------------------------------------------------------------------------
# START THE GUI LOOP
# -----------------------------------------------------------------------------
# This starts Tkinter's event processing loop, so the window remains open.
root.mainloop()
