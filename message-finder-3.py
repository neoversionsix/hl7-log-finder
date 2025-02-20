"""
HL7 Log Finder GUI
- Dark Theme
- Single Default Search Term
- Countdown Progress Bar from 100% to 0%
- Timeout Warning Popup
- Color-Changing Run Button (green -> red -> green)
- Date Pickers with dd/mmm/yyyy format
- "Date Greater Than" defaults to (Today - 2 days)
- HTML output includes a Copy button under each <pre> block
"""

import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from tkcalendar import DateEntry

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
    Inserts a log message into the console widget and forces an update.
    Also prints to the standard console (optional).
    """
    console_text.insert(tk.END, msg + "\n")
    console_text.see(tk.END)
    print(msg)

def reset_ui():
    """
    Re-enable the Run button (green style), reset the progress bar to 100%, and set status to idle.
    """
    btn_run.config(style="GreenButton.TButton", state='normal')
    status_var.set("Status: Idle")
    progress_bar['value'] = 100  # reset to full
    # No need to 'stop' because we're in determinate mode

def run_search():
    """
    Executes the HL7 log search process:
    1. Reads user inputs (dates, search terms, timeout).
    2. Validates inputs and sets up the output HTML file.
    3. Iterates over folders/files, searching for HL7 messages containing all search terms.
    4. Each iteration updates the countdown progress bar from 100% -> 0% over 'timeout_seconds'.
    5. Writes matches to a timestamped HTML file, each with a Copy button.
    6. If timeout is reached, stops and warns the user.
    7. Button returns to green after completion.
    """
    # Change the Run Search button to red
    btn_run.config(style="RedButton.TButton", state='disabled')
    status_var.set("Status: Searching...")
    console_text.delete('1.0', tk.END)  # Clear previous log output

    # Initialize the progress bar for a 100%->0% countdown
    progress_bar.config(mode='determinate', maximum=100)
    progress_bar['value'] = 100

    # Force a quick GUI update so the button color and progress bar show immediately
    root.update()

    start_time = datetime.datetime.now()

    # ---------------------------
    # 1. Retrieve and Validate User Inputs
    # ---------------------------
    date_greater_str = date_to_YYYYMMDD(date_greater_entry.get_date())
    date_less_str    = date_to_YYYYMMDD(date_less_entry.get_date())

    terms = [entry.get().strip() for entry in search_term_entries if entry.get().strip()]
    if not terms:
        messagebox.showerror("Input Error", "Please enter at least one search term.")
        reset_ui()
        return

    # Timeout in seconds
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

    # HTML header with JavaScript for copy-to-clipboard
    output_lines = [
        "<html><head><meta charset='UTF-8'><title>HL7 Search Results</title>\n",
        "<script>\n",
        "function copyToClipboard(elemId) {\n",
        "  var text = document.getElementById(elemId).innerText;\n",
        "  navigator.clipboard.writeText(text)\n",
        "    .then(() => alert('Copied to clipboard'))\n",
        "    .catch(err => console.error('Failed to copy text', err));\n",
        "}\n",
        "</script>\n",
        "</head><body>\n",
        "<h1>HL7 Search Results</h1>\n"
    ]

    msg_counter = 1  # unique ID for each <pre> block

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
        # Update progress bar countdown
        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        time_left = timeout_seconds - elapsed
        if time_left < 0:
            time_left = 0
        progress_bar['value'] = (time_left / timeout_seconds) * 100
        root.update()

        if time_left <= 0:
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
            # Update progress bar countdown
            elapsed = (datetime.datetime.now() - start_time).total_seconds()
            time_left = timeout_seconds - elapsed
            if time_left < 0:
                time_left = 0
            progress_bar['value'] = (time_left / timeout_seconds) * 100
            root.update()

            if time_left <= 0:
                timeout_occurred = True
                log_message("Timeout reached: Stopping search and outputting partial results.")
                break

            file_path = os.path.join(folder_path, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as infile:
                    read_data = infile.read()
            except Exception as e:
                log_message(f"Skipping file '{file_path}' due to error: {e}")
                continue

            # Split the file content into HL7 messages using '======'
            hl7_list = read_data.split('======')
            for hl7_message in hl7_list:
                # Check if the HL7 message contains all of the search terms
                if all(term in hl7_message for term in terms):
                    log_message(f"Found match in: {file_path}")
                    # Insert <pre> block with unique ID and a copy button
                    output_lines.append(f"<h2>{file_path}</h2>\n")
                    output_lines.append(f"<pre id='msg_{msg_counter}'>{hl7_message}</pre>\n")
                    output_lines.append(f"<button onclick=\"copyToClipboard('msg_{msg_counter}')\">Copy</button><br/>\n")
                    msg_counter += 1

        if timeout_occurred:
            break

    # If a timeout occurred, show a pop-up warning
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

def date_to_YYYYMMDD(date_obj):
    """
    Converts a Python date object into a YYYYMMDD string.
    
    Example:
        datetime.date(2025, 1, 15) -> '20250115'
    """
    return date_obj.strftime('%Y%m%d')

# ---------------------------
# GUI Setup
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

# 1. Date Pickers (with dd/mmm/yyyy pattern)
ttk.Label(frame, text="Date Greater Than:").grid(row=0, column=0, sticky=tk.W)
date_greater_entry = DateEntry(frame, width=12, date_pattern="yyyy/mm/dd")
date_greater_entry.grid(row=0, column=1, padx=5, pady=5)
# Default to 2 days ago
two_days_ago = datetime.date.today() - datetime.timedelta(days=2)
date_greater_entry.set_date(two_days_ago)

ttk.Label(frame, text="Date Less Than:").grid(row=1, column=0, sticky=tk.W)
date_less_entry = DateEntry(frame, width=12, date_pattern="yyyy/mm/dd")
date_less_entry.grid(row=1, column=1, padx=5, pady=5)
# Optionally set a default for 'less than' if you want, e.g. today or tomorrow
# date_less_entry.set_date(datetime.date.today())

# 2. Search Term Fields with "Add Search Term" Button
ttk.Label(frame, text="Search Terms:").grid(row=2, column=0, sticky=tk.NW)
frame_search_terms = ttk.Frame(frame)
frame_search_terms.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
# Create a single initial search term field
add_search_term_field("9999999")

btn_add_term = ttk.Button(frame, text="Add Search Term", command=lambda: add_search_term_field())
btn_add_term.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

# 3. Timeout Entry Field
ttk.Label(frame, text="Timeout (seconds):").grid(row=4, column=0, sticky=tk.W)
entry_timeout = ttk.Entry(frame, width=10)
entry_timeout.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)
entry_timeout.insert(0, "30")  # Default timeout value

# 4. Run Search Button (Green by default)
btn_run = ttk.Button(frame, text="Run Search", command=run_search, style="GreenButton.TButton")
btn_run.grid(row=5, column=0, columnspan=2, pady=10)

# 5. Status Label and Progress Bar
status_var = tk.StringVar()
status_var.set("Status: Idle")
status_label = ttk.Label(frame, textvariable=status_var)
status_label.grid(row=6, column=0, columnspan=2, sticky=tk.W)

progress_bar = ttk.Progressbar(frame, orient='horizontal', mode='determinate', length=200)
progress_bar.grid(row=7, column=0, columnspan=2, pady=5)
progress_bar['maximum'] = 100
progress_bar['value'] = 100  # Start full

# 6. Console Text Widget for Log Output
ttk.Label(root, text="Console Output:").grid(row=1, column=0, sticky=tk.W, padx=10)
console_text = ScrolledText(root, width=80, height=20, wrap=tk.WORD, bg="#3e3e3e", fg="white", insertbackground="white")
console_text.grid(row=2, column=0, padx=10, pady=5)

# Start the Tkinter event loop
root.mainloop()
