"""
HL7 Log Finder GUI with Calendar Date Pickers and Enhanced Features

Features:
- Calendar-based date selection for "Date Greater Than" and "Date Less Than".
- Comma-separated multiple search terms (e.g. "THUY, ABC123, TestString").
- Searches HL7 log files within a date range based on folder names.
- Shows a live console log and status messages in the GUI.
- Disables the search button while processing to prevent repeated clicks.
- Includes a timeout field (default 30 seconds) to stop the search if it takes too long.
- Writes matching HL7 messages to a timestamped HTML file in an 'output' subfolder.
- Displays errors to the user via message boxes.

Dependencies:
- tkcalendar (install with: pip install tkcalendar)
- tkinter (built-in)
"""

import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText  # Provides a scrollable text widget for console output
from tkcalendar import DateEntry  # Calendar-based date selection widget

def date_to_YYYYMMDD(date_obj):
    """
    Converts a Python date object (from DateEntry) into a YYYYMMDD string.
    
    Example:
        datetime.date(2025, 1, 15) -> '20250115'
    """
    return date_obj.strftime('%Y%m%d')

def log_message(msg):
    """
    Inserts a log message into the console widget and forces an update.
    Also prints to the standard console (optional).
    """
    console_text.insert(tk.END, msg + "\n")
    console_text.see(tk.END)  # Scroll to the end
    # Also print to system console if desired:
    print(msg)

def run_search():
    """
    Executes the HL7 log search:
    1. Reads user inputs (dates, search terms, and timeout).
    2. Validates input and sets up the output HTML file.
    3. Iterates over folders (named by date) and files to find HL7 messages matching all search terms.
    4. Stops processing if the search exceeds the user-defined timeout.
    5. Writes the collected messages to an HTML file and logs progress to the GUI console.
    """
    # Disable the Run Search button and update the status to prevent re-clicks during processing.
    btn_run.config(state='disabled')
    status_var.set("Status: Searching... Please wait.")
    console_text.delete('1.0', tk.END)  # Clear previous console output

    # Record the search start time to enforce the timeout
    start_time = datetime.datetime.now()

    # -------------------------------------------------------------------------
    # 1. Retrieve and validate user inputs
    # -------------------------------------------------------------------------
    # Convert DateEntry selections into YYYYMMDD string format
    date_greater_str = date_to_YYYYMMDD(date_greater_entry.get_date())
    date_less_str    = date_to_YYYYMMDD(date_less_entry.get_date())

    # Get the user-entered comma-separated search terms and remove extraneous spaces
    search_terms_str = entry_search_terms.get().strip()
    if not search_terms_str:
        messagebox.showerror("Input Error", "Please enter at least one search term.")
        btn_run.config(state='normal')
        status_var.set("Status: Idle")
        return
    terms = [term.strip() for term in search_terms_str.split(',') if term.strip()]

    # Get and validate the timeout value; use 30 seconds if conversion fails.
    try:
        timeout_seconds = int(entry_timeout.get().strip())
    except ValueError:
        timeout_seconds = 30

    # Validate date range: the start date must be strictly less than the end date.
    try:
        date_greater_than = int(date_greater_str)
        date_less_than    = int(date_less_str)
    except ValueError:
        messagebox.showerror("Input Error", "Error converting dates. Please re-check your selections.")
        btn_run.config(state='normal')
        status_var.set("Status: Idle")
        return
    if date_greater_than >= date_less_than:
        messagebox.showerror("Input Error", "'Date Greater Than' must be strictly less than 'Date Less Than'.")
        btn_run.config(state='normal')
        status_var.set("Status: Idle")
        return

    # -------------------------------------------------------------------------
    # 2. Setup output HTML file
    # -------------------------------------------------------------------------
    # Generate a timestamp string to uniquely name the output file
    timestamp_str = datetime.datetime.now().isoformat().replace(':', '-').replace('.', '_')
    filename = f'OUTPUT-{timestamp_str}.html'  # Output file now in HTML format

    # Determine the script's directory and create an 'output' folder if it doesn't exist
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    output_folder = os.path.join(script_dir, 'output')
    os.makedirs(output_folder, exist_ok=True)
    output_file_path = os.path.join(output_folder, filename)

    # Initialize a list to store HTML-formatted search results
    output_lines = [
        "<html><head><meta charset='UTF-8'><title>HL7 Search Results</title></head><body>\n",
        "<h1>HL7 Search Results</h1>\n"
    ]

    # -------------------------------------------------------------------------
    # 3. Search for HL7 messages in the network share
    # -------------------------------------------------------------------------
    network_share_path = r'\\whsrhaparch1\RhapsodyHL7FileLogs_Prod\MasterLog'
    try:
        files_or_folders = os.listdir(network_share_path)
    except Exception as e:
        messagebox.showerror("Network Error", f"Could not list directory:\n{str(e)}")
        btn_run.config(state='normal')
        status_var.set("Status: Idle")
        return

    # Filter to include only folder names (exclude files ending with '.zip')
    folders = [item for item in files_or_folders if not item.endswith('zip')]
    # Select folders where the first 8 characters are a date within the specified range
    filtered_folders = [
        folder for folder in folders
        if len(folder) >= 8 and folder[:8].isdigit() and date_greater_than < int(folder[:8]) < date_less_than
    ]

    log_message("Starting HL7 search...")
    log_message("Console Output:")

    timeout_occurred = False  # Flag to indicate if timeout was reached

    # Loop over each folder that falls within the date range
    for folder_name in filtered_folders:
        # Check for timeout after processing each folder
        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        if elapsed > timeout_seconds:
            log_message("Timeout reached: Not all messages were searched. Outputting partial results.")
            timeout_occurred = True
            break

        folder_path = os.path.join(network_share_path, folder_name)
        try:
            files_in_folder = os.listdir(folder_path)
        except Exception as e:
            log_message(f"Skipping folder '{folder_name}' due to error: {e}")
            continue

        # Loop over each file in the current folder
        for file_name in files_in_folder:
            # Check timeout after each file as well
            elapsed = (datetime.datetime.now() - start_time).total_seconds()
            if elapsed > timeout_seconds:
                log_message("Timeout reached: Not all messages were searched. Outputting partial results.")
                timeout_occurred = True
                break

            file_path = os.path.join(folder_path, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as infile:
                    read_data = infile.read()
            except Exception as e:
                log_message(f"Skipping file '{file_path}' due to error: {e}")
                continue

            # Split the file content into HL7 messages using '======' as delimiter
            hl7_list = read_data.split('======')
            for hl7_message in hl7_list:
                # Check if the HL7 message contains all of the search terms (change to "any" if desired)
                if all(term in hl7_message for term in terms):
                    log_message(f'Found match in: {file_path}')
                    log_message(hl7_message)
                    # Append results to the HTML output with proper tags
                    output_lines.append(f"<h2>{file_path}</h2>\n")
                    output_lines.append(f"<pre>{hl7_message}</pre>\n")
        if timeout_occurred:
            break

    # Close the HTML document structure
    output_lines.append("</body></html>\n")

    # -------------------------------------------------------------------------
    # 4. Write the HTML output file and finalize the search
    # -------------------------------------------------------------------------
    try:
        with open(output_file_path, 'w', encoding='utf-8') as outfile:
            outfile.writelines(output_lines)
        messagebox.showinfo("Success", f"Search complete!\n\nResults saved to:\n{output_file_path}")
        log_message(f"Successfully wrote output to {output_file_path}")
    except Exception as e:
        err_msg = f"Error writing to file: {e}\nPrinting results to console instead."
        messagebox.showerror("File Write Error", err_msg)
        log_message(err_msg)
        log_message(''.join(output_lines))

    # Re-enable the Run Search button and update the status to idle after search completes
    btn_run.config(state='normal')
    status_var.set("Status: Idle")

# ---------------------------------------------------------------------------
# GUI Setup
# ---------------------------------------------------------------------------
root = tk.Tk()
root.title("HL7 Log Finder")
root.resizable(False, False)  # Fixed window size

# Main frame to hold controls with padding
frame = ttk.Frame(root, padding="10 10 10 10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E))

# ---------------------------
# 1. Date Greater Than Picker
# ---------------------------
ttk.Label(frame, text="Date Greater Than:").grid(row=0, column=0, sticky=tk.W)
date_greater_entry = DateEntry(frame, width=12, date_pattern="yyyy/mm/dd")
date_greater_entry.grid(row=0, column=1, padx=5, pady=5)

# ---------------------------
# 2. Date Less Than Picker
# ---------------------------
ttk.Label(frame, text="Date Less Than:").grid(row=1, column=0, sticky=tk.W)
date_less_entry = DateEntry(frame, width=12, date_pattern="yyyy/mm/dd")
date_less_entry.grid(row=1, column=1, padx=5, pady=5)

# ---------------------------
# 3. Search Terms Entry (comma-separated)
# ---------------------------
ttk.Label(frame, text="Search Terms (comma-separated):").grid(row=2, column=0, sticky=tk.W)
entry_search_terms = ttk.Entry(frame, width=30)
entry_search_terms.grid(row=2, column=1, padx=5, pady=5)
entry_search_terms.insert(0, "THUY, ABC123")  # Example placeholder

# ---------------------------
# 4. Timeout Entry (in seconds)
# ---------------------------
ttk.Label(frame, text="Timeout (seconds):").grid(row=3, column=0, sticky=tk.W)
entry_timeout = ttk.Entry(frame, width=10)
entry_timeout.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
entry_timeout.insert(0, "30")  # Default timeout value

# ---------------------------
# 5. Run Search Button
# ---------------------------
btn_run = ttk.Button(frame, text="Run Search", command=run_search)
btn_run.grid(row=4, column=0, columnspan=2, pady=10)

# ---------------------------
# 6. Status Label
# ---------------------------
status_var = tk.StringVar()
status_var.set("Status: Idle")
status_label = ttk.Label(frame, textvariable=status_var)
status_label.grid(row=5, column=0, columnspan=2, sticky=tk.W)

# ---------------------------
# 7. Console Text Widget (for log output)
# ---------------------------
ttk.Label(root, text="Console Output:").grid(row=1, column=0, sticky=tk.W, padx=10)
console_text = ScrolledText(root, width=80, height=20, wrap=tk.WORD)
console_text.grid(row=2, column=0, padx=10, pady=5)

# Start the Tkinter event loop.
root.mainloop()
