"""
HL7 Log Finder GUI with Dark Theme, Single Default Search Term, Timeout Warning, 
Progress Bar, and Color-Changing Run Button

In this version:
- Only one search term field is shown by default (prefilled with "9999999").
- The user can add more search terms if needed.
- The Run Search button turns red during search, then back to green.
- The progress bar animates by calling root.update() inside the loops.
"""

import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText  # Scrollable text widget for console output
from tkcalendar import DateEntry  # Calendar-based date selection widget

# ---------------------------
# Helper Functions and Globals
# ---------------------------
search_term_entries = []  # List to hold individual search term Entry widgets

def add_search_term_field(default_text=""):
    """
    Creates a new search term Entry widget in the search term frame and appends it to the global list.
    """
    entry = ttk.Entry(frame_search_terms, width=30)
    entry.grid(row=len(search_term_entries), column=0, padx=5, pady=2, sticky=tk.W)
    entry.insert(0, default_text)
    search_term_entries.append(entry)

def log_message(msg):
    """
    Inserts a log message into the console widget (without printing individual HL7 messages)
    and forces an update. Also prints to the standard console.
    """
    console_text.insert(tk.END, msg + "\n")
    console_text.see(tk.END)
    print(msg)

def run_search():
    """
    Executes the HL7 log search process:
    1. Reads user inputs (dates, individual search terms, and timeout).
    2. Validates input and sets up the output HTML file.
    3. Iterates over folders (named by date) and files to find HL7 messages matching all search terms.
    4. Checks the elapsed time and stops if the search exceeds the user-defined timeout.
    5. Writes the collected messages to an HTML file and logs progress to the GUI console.
    6. Uses a progress bar to indicate ongoing processing.
    7. Periodically calls root.update() so the GUI remains somewhat responsive.
    """
    # Change the Run Search button to red and start progress bar
    btn_run.config(style="RedButton.TButton", state='disabled')
    status_var.set("Status: Searching...")
    progress_bar.start(10)
    console_text.delete('1.0', tk.END)  # Clear previous log output

    # Force a quick GUI update so the button color and progress bar start immediately
    root.update()

    # Record the start time for timeout enforcement
    start_time = datetime.datetime.now()

    # ---------------------------
    # 1. Retrieve and Validate User Inputs
    # ---------------------------
    # Convert the DateEntry selections to YYYYMMDD format
    date_greater_str = date_to_YYYYMMDD(date_greater_entry.get_date())
    date_less_str    = date_to_YYYYMMDD(date_less_entry.get_date())

    # Gather individual search term entries and ignore blank ones
    terms = [entry.get().strip() for entry in search_term_entries if entry.get().strip()]
    if not terms:
        messagebox.showerror("Input Error", "Please enter at least one search term.")
        reset_ui()
        return

    # Get and validate the timeout value (default to 30 seconds if invalid)
    try:
        timeout_seconds = int(entry_timeout.get().strip())
    except ValueError:
        timeout_seconds = 30

    try:
        date_greater_than = int(date_greater_str)
        date_less_than    = int(date_less_str)
    except ValueError:
        messagebox.showerror("Input Error", "Error converting dates. Please re-check your selections.")
        reset_ui()
        return

    if date_greater_than >= date_less_than:
        messagebox.showerror("Input Error", "'Date Greater Than' must be strictly less than 'Date Less Than'.")
        reset_ui()
        return

    # ---------------------------
    # 2. Setup Output HTML File
    # ---------------------------
    timestamp_str = datetime.datetime.now().isoformat().replace(':', '-').replace('.', '_')
    filename = f'OUTPUT-{timestamp_str}.html'
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    output_folder = os.path.join(script_dir, 'output')
    os.makedirs(output_folder, exist_ok=True)
    output_file_path = os.path.join(output_folder, filename)
    
    output_lines = [
        "<html><head><meta charset='UTF-8'><title>HL7 Search Results</title></head><body>\n",
        "<h1>HL7 Search Results</h1>\n"
    ]

    # ---------------------------
    # 3. Search for HL7 Messages
    # ---------------------------
    network_share_path = r'\\whsrhaparch1\RhapsodyHL7FileLogs_Prod\MasterLog'
    try:
        files_or_folders = os.listdir(network_share_path)
    except Exception as e:
        messagebox.showerror("Network Error", f"Could not list directory:\n{str(e)}")
        reset_ui()
        return

    folders = [item for item in files_or_folders if not item.endswith('zip')]
    filtered_folders = [
        folder for folder in folders
        if len(folder) >= 8 and folder[:8].isdigit() and date_greater_than < int(folder[:8]) < date_less_than
    ]

    log_message("Starting HL7 search...")

    timeout_occurred = False

    for folder_name in filtered_folders:
        # Check for timeout after each folder
        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        if elapsed > timeout_seconds:
            timeout_occurred = True
            log_message("Timeout reached: Stopping search and outputting partial results.")
            break

        folder_path = os.path.join(network_share_path, folder_name)
        try:
            files_in_folder = os.listdir(folder_path)
        except Exception as e:
            log_message(f"Skipping folder '{folder_name}' due to error: {e}")
            continue

        for file_name in files_in_folder:
            elapsed = (datetime.datetime.now() - start_time).total_seconds()
            if elapsed > timeout_seconds:
                timeout_occurred = True
                log_message("Timeout reached: Stopping search and outputting partial results.")
                break

            file_path = os.path.join(folder_path, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as infile:
                    read_data = infile.read()
            except Exception as e:
                log_message(f"Skipping file '{file_path}' due to error: {e}")
                # Periodically update the UI
                root.update()
                continue

            # Split the file content into HL7 messages using '======'
            hl7_list = read_data.split('======')
            for hl7_message in hl7_list:
                # Check if the HL7 message contains all of the search terms
                if all(term in hl7_message for term in terms):
                    # Only log the file path (not the entire HL7 message)
                    log_message(f"Found match in: {file_path}")
                    output_lines.append(f"<h2>{file_path}</h2>\n")
                    output_lines.append(f"<pre>{hl7_message}</pre>\n")

            # After each file, let the GUI update so the progress bar can move
            root.update()

        if timeout_occurred:
            break

    # If a timeout occurred, show a pop-up warning once.
    if timeout_occurred:
        messagebox.showwarning("Timeout", "Timeout reached: Not all messages were searched. Partial results will be output.")

    output_lines.append("</body></html>\n")

    # ---------------------------
    # 4. Write the HTML Output File
    # ---------------------------
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

    # ---------------------------
    # 5. Reset the UI State
    # ---------------------------
    reset_ui()

def reset_ui():
    """
    Re-enable the Run button (green style), stop the progress bar, and set status to idle.
    """
    btn_run.config(style="GreenButton.TButton", state='normal')
    status_var.set("Status: Idle")
    progress_bar.stop()

def date_to_YYYYMMDD(date_obj):
    """
    Converts a Python date object (from DateEntry) into a YYYYMMDD string.
    
    Example:
        datetime.date(2025, 1, 15) -> '20250115'
    """
    return date_obj.strftime('%Y%m%d')

# ---------------------------
# GUI Setup and Dark Theme Configuration
# ---------------------------
root = tk.Tk()
root.title("HL7 Log Finder")
root.resizable(False, False)

# Set dark colors for the app
root.tk_setPalette(background="#2e2e2e", foreground="white", activeBackground="#3e3e3e", activeForeground="white")
style = ttk.Style(root)
style.theme_use('clam')

# Configure general styles
style.configure("TLabel", background="#2e2e2e", foreground="white")
style.configure("TButton", background="#3e3e3e", foreground="white")
style.configure("TEntry", fieldbackground="#3e3e3e", foreground="white")
style.configure("TFrame", background="#2e2e2e")

# Define two custom button styles: green (idle) and red (running)
style.configure("GreenButton.TButton", background="green", foreground="white")
style.map("GreenButton.TButton",
          background=[("active", "#228B22")])  # Darker green on hover

style.configure("RedButton.TButton", background="red", foreground="white")
style.map("RedButton.TButton",
          background=[("active", "#8B0000")])  # Darker red on hover

# Main frame for controls
frame = ttk.Frame(root, padding="10 10 10 10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E))

# ---------------------------
# 1. Date Pickers for Start and End Dates
# ---------------------------
ttk.Label(frame, text="Date Greater Than:").grid(row=0, column=0, sticky=tk.W)
date_greater_entry = DateEntry(frame, width=12, date_pattern="yyyy/mm/dd")
date_greater_entry.grid(row=0, column=1, padx=5, pady=5)

ttk.Label(frame, text="Date Less Than:").grid(row=1, column=0, sticky=tk.W)
date_less_entry = DateEntry(frame, width=12, date_pattern="yyyy/mm/dd")
date_less_entry.grid(row=1, column=1, padx=5, pady=5)

# ---------------------------
# 2. Search Term Fields with "Add Search Term" Button
# ---------------------------
ttk.Label(frame, text="Search Terms:").grid(row=2, column=0, sticky=tk.NW)
# Frame to hold individual search term entry fields
frame_search_terms = ttk.Frame(frame)
frame_search_terms.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

# Create a single initial search term field, prefilled with "9999999"
add_search_term_field("9999999")

# Button to add another search term field
btn_add_term = ttk.Button(frame, text="Add Search Term", command=lambda: add_search_term_field())
btn_add_term.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

# ---------------------------
# 3. Timeout Entry Field
# ---------------------------
ttk.Label(frame, text="Timeout (seconds):").grid(row=4, column=0, sticky=tk.W)
entry_timeout = ttk.Entry(frame, width=10)
entry_timeout.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)
entry_timeout.insert(0, "30")  # Default timeout value

# ---------------------------
# 4. Run Search Button (Green by default)
# ---------------------------
btn_run = ttk.Button(frame, text="Run Search", command=run_search, style="GreenButton.TButton")
btn_run.grid(row=5, column=0, columnspan=2, pady=10)

# ---------------------------
# 5. Status Label and Progress Bar
# ---------------------------
status_var = tk.StringVar()
status_var.set("Status: Idle")
status_label = ttk.Label(frame, textvariable=status_var)
status_label.grid(row=6, column=0, columnspan=2, sticky=tk.W)

progress_bar = ttk.Progressbar(frame, orient='horizontal', mode='indeterminate', length=200)
progress_bar.grid(row=7, column=0, columnspan=2, pady=5)

# ---------------------------
# 6. Console Text Widget for Log Output
# ---------------------------
ttk.Label(root, text="Console Output:").grid(row=1, column=0, sticky=tk.W, padx=10)
console_text = ScrolledText(root, width=80, height=20, wrap=tk.WORD, bg="#3e3e3e", fg="white", insertbackground="white")
console_text.grid(row=2, column=0, padx=10, pady=5)

# Start the Tkinter event loop.
root.mainloop()
