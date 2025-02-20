"""
HL7 Log Finder GUI with Threading and Open-in-Browser Popup
- Dark Theme
- Single Default Search Term
- Countdown Progress Bar from 100% to 0%
- Timeout Warning Popup
- Color-Changing Run Button (green -> red -> green)
- "Date Greater Than" defaults to (Today - 2 days)
- Valid tkcalendar date pattern "yyyy/mm/dd"
- Background thread for searching to keep GUI responsive
- Copy button omits the first line of the HL7 message
- On success, a popup lets you open the saved HTML file in your browser
"""

import os
import datetime
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from tkcalendar import DateEntry
import webbrowser  # for opening the file in a browser

# ---------------------------
# Global Flags / Variables
# ---------------------------
search_thread = None         # Will hold our background search thread
search_start_time = None     # When the search began (for the countdown)
timeout_seconds = 30         # Default, can be changed by user
stop_search = False          # Main thread sets this to True if time is up
search_done = False          # The worker thread sets this to True when finished
search_timed_out = False     # Set to True if we actually hit the timeout
log_queue = queue.Queue()    # Thread-safe queue for log messages
error_msg = None             # Will hold any network/IO error from the thread
output_file_path = None      # Final output path, for success message

search_term_entries = []     # Holds individual search term Entry widgets
output_lines = []            # Collected HTML lines from the search

def add_search_term_field(default_text=""):
    """
    Creates a new search term Entry widget in the search term frame and appends it to the global list.
    """
    entry = ttk.Entry(frame_search_terms, width=30)
    entry.grid(row=len(search_term_entries), column=0, padx=5, pady=2, sticky=tk.W)
    entry.insert(0, default_text)
    search_term_entries.append(entry)

def log_message_threadsafe(msg):
    """
    Put a log message into the thread-safe queue for the main thread to display.
    """
    log_queue.put(msg)

def process_log_queue():
    """
    Periodically called in the main thread to move queued log messages into the console.
    """
    while not log_queue.empty():
        msg = log_queue.get_nowait()
        console_text.insert(tk.END, msg + "\n")
        console_text.see(tk.END)
    # Schedule the next check
    root.after(200, process_log_queue)

def reset_ui():
    """
    Re-enable the Run button (green style), reset the progress bar, set status to idle.
    """
    btn_run.config(style="GreenButton.TButton", state='normal')
    status_var.set("Status: Idle")
    progress_bar['value'] = 100

def show_success_popup(file_path):
    """
    Creates a custom popup that displays the saved HTML file path and has a button
    to open the file in the browser.
    """
    popup = tk.Toplevel(root)
    popup.title("Search Complete")
    popup.configure(background="#2e2e2e")
    # Make the popup modal
    popup.grab_set()
    
    label = tk.Label(popup, text=f"Search complete!\nResults saved to:\n{file_path}", 
                     background="#2e2e2e", foreground="white", justify="center")
    label.pack(padx=20, pady=20)
    
    def open_file():
        webbrowser.open(file_path)
        popup.destroy()
    
    btn_open = ttk.Button(popup, text="Open in Browser", command=open_file)
    btn_open.pack(side="left", padx=(20,10), pady=10)
    
    btn_close = ttk.Button(popup, text="Close", command=popup.destroy)
    btn_close.pack(side="right", padx=(10,20), pady=10)
    
    popup.wait_window(popup)

def start_search():
    """
    Called when user clicks Run Search. Sets up UI, spawns the background thread, and starts
    the periodic checks (update_progress_bar, process_log_queue).
    """
    global stop_search, search_done, search_timed_out, error_msg, output_file_path
    global search_start_time, timeout_seconds, output_lines

    # Reset flags
    stop_search = False
    search_done = False
    search_timed_out = False
    error_msg = None
    output_lines = []

    # Change the Run Search button to red and clear console
    btn_run.config(style="RedButton.TButton", state='disabled')
    status_var.set("Status: Searching...")
    console_text.delete('1.0', tk.END)

    # Initialize the progress bar
    progress_bar.config(mode='determinate', maximum=100)
    progress_bar['value'] = 100

    # Read user inputs
    # 1) Timeout
    try:
        t_val = int(entry_timeout.get().strip())
        if t_val < 1:
            t_val = 30
    except ValueError:
        t_val = 30
    timeout_seconds = t_val

    # 2) Date range
    date_greater_str = date_to_YYYYMMDD(date_greater_entry.get_date())
    date_less_str    = date_to_YYYYMMDD(date_less_entry.get_date())
    try:
        date_greater_than = int(date_greater_str)
        date_less_than    = int(date_less_str)
        if date_greater_than >= date_less_than:
            messagebox.showerror("Input Error", "'Date Greater Than' must be strictly less than 'Date Less Than'.")
            reset_ui()
            return
    except ValueError:
        messagebox.showerror("Input Error", "Error converting dates. Please re-check your selections.")
        reset_ui()
        return

    # 3) Search terms
    terms = [entry.get().strip() for entry in search_term_entries if entry.get().strip()]
    if not terms:
        messagebox.showerror("Input Error", "Please enter at least one search term.")
        reset_ui()
        return

    # 4) Prepare output file
    global script_dir
    timestamp_str = datetime.datetime.now().isoformat().replace(':', '-').replace('.', '_')
    fname = f'OUTPUT-{timestamp_str}.html'
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    out_dir = os.path.join(script_dir, 'output')
    os.makedirs(out_dir, exist_ok=True)
    output_file_path = os.path.join(out_dir, fname)

    # Collect initial HTML lines (with copy-to-clipboard JavaScript that omits the first line)
    output_lines.append("<html><head><meta charset='UTF-8'><title>HL7 Search Results</title>\n")
    output_lines.append("<script>\n")
    output_lines.append("function copyToClipboard(elemId) {\n")
    output_lines.append("  var text = document.getElementById(elemId).innerText;\n")
    output_lines.append("  // Remove the first line (e.g., [SENT] or [RECEIVED])\n")
    output_lines.append("  var lines = text.split('\\n');\n")
    output_lines.append("  if (lines.length > 0) { lines.shift(); }\n")
    output_lines.append("  text = lines.join('\\n');\n")
    output_lines.append("  navigator.clipboard.writeText(text)\n")
    output_lines.append("    .then(() => alert('Copied to clipboard'))\n")
    output_lines.append("    .catch(err => console.error('Failed to copy text', err));\n")
    output_lines.append("}\n")
    output_lines.append("</script>\n")
    output_lines.append("</head><body>\n")
    output_lines.append("<h1>HL7 Search Results</h1>\n")

    # Record the start time
    search_start_time = datetime.datetime.now()

    # Spawn background thread
    def search_logic():
        global search_done, search_timed_out, error_msg, output_lines
        msg_counter = 1

        network_share_path = r'\\whsrhaparch1\RhapsodyHL7FileLogs_Prod\MasterLog'
        try:
            files_or_folders = os.listdir(network_share_path)
        except Exception as e:
            error_msg = f"Network Error: Could not list directory:\n{str(e)}"
            search_done = True
            return

        # Filter date folders
        folders = [item for item in files_or_folders if not item.endswith('zip')]
        filtered_folders = [
            folder for folder in folders
            if len(folder) >= 8 and folder[:8].isdigit() and date_greater_than < int(folder[:8]) < date_less_than
        ]

        log_message_threadsafe("Starting HL7 search...")

        for folder_name in filtered_folders:
            if stop_search:
                search_timed_out = True
                break

            folder_path = os.path.join(network_share_path, folder_name)
            try:
                files_in_folder = os.listdir(folder_path)
            except Exception as e:
                log_message_threadsafe(f"Skipping folder '{folder_name}' due to error: {e}")
                continue

            for file_name in files_in_folder:
                if stop_search:
                    search_timed_out = True
                    break

                file_path = os.path.join(folder_path, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as infile:
                        read_data = infile.read()
                except Exception as e:
                    log_message_threadsafe(f"Skipping file '{file_path}' due to error: {e}")
                    continue

                # Split file content into HL7 messages
                hl7_list = read_data.split('======')
                for hl7_message in hl7_list:
                    if all(term in hl7_message for term in terms):
                        log_message_threadsafe(f"Found match in: {file_path}")
                        output_lines.append(f"<h2>{file_path}</h2>\n")
                        output_lines.append(f"<pre id='msg_{msg_counter}'>{hl7_message}</pre>\n")
                        output_lines.append(f"<button onclick=\"copyToClipboard('msg_{msg_counter}')\">Copy</button><br/>\n")
                        msg_counter += 1

            if stop_search:
                break

        output_lines.append("</body></html>\n")

        # Write to file if no critical error
        try:
            with open(output_file_path, 'w', encoding='utf-8') as outfile:
                outfile.writelines(output_lines)
        except Exception as e:
            error_msg = f"Error writing to file: {e}"

        search_done = True

    global search_thread
    search_thread = threading.Thread(target=search_logic, daemon=True)
    search_thread.start()

    # Start periodic checks
    update_progress_bar()
    process_log_queue()

def update_progress_bar():
    """
    Runs in the main thread every 100 ms:
    - Updates the countdown bar from 100% down to 0% based on elapsed time.
    - If time is up, sets stop_search = True.
    - If the search thread is done, handle final UI messages.
    - Otherwise, schedule another call.
    """
    global stop_search, search_done, search_timed_out, error_msg

    if search_done:
        progress_bar['value'] = 0
        finalize_search()
        return

    elapsed = (datetime.datetime.now() - search_start_time).total_seconds()
    time_left = timeout_seconds - elapsed
    if time_left <= 0:
        time_left = 0
        stop_search = True

    percent = (time_left / timeout_seconds) * 100 if timeout_seconds > 0 else 0
    progress_bar['value'] = percent

    root.after(100, update_progress_bar)

def finalize_search():
    """
    Called once the background thread has finished.
    Shows any warnings or errors, resets the UI, and logs final messages.
    If successful, displays a popup with an "Open in Browser" button.
    """
    global search_timed_out, error_msg, output_file_path

    if search_timed_out:
        messagebox.showwarning("Timeout", "Timeout reached: Not all messages were searched. Partial results have been output.")

    if error_msg:
        messagebox.showerror("Error", error_msg)
        log_message_threadsafe(error_msg)
    else:
        show_success_popup(output_file_path)
        log_message_threadsafe(f"Successfully wrote output to {output_file_path}")

    reset_ui()

def date_to_YYYYMMDD(date_obj):
    """
    Converts a Python date object into a YYYYMMDD string.
    Example: datetime.date(2025, 1, 15) -> '20250115'
    """
    return date_obj.strftime('%Y%m%d')

# ---------------------------
# GUI Setup
# ---------------------------
root = tk.Tk()
root.title("HL7 Log Finder")
root.resizable(False, False)

root.tk_setPalette(background="#2e2e2e", foreground="white", activeBackground="#3e3e3e", activeForeground="white")
style = ttk.Style(root)
style.theme_use('clam')

style.configure("TLabel", background="#2e2e2e", foreground="white")
style.configure("TButton", background="#3e3e3e", foreground="white")
style.configure("TEntry", fieldbackground="#3e3e3e", foreground="white")
style.configure("TFrame", background="#2e2e2e")

style.configure("GreenButton.TButton", background="green", foreground="white")
style.map("GreenButton.TButton", background=[("active", "#228B22")])
style.configure("RedButton.TButton", background="red", foreground="white")
style.map("RedButton.TButton", background=[("active", "#8B0000")])

frame = ttk.Frame(root, padding="10 10 10 10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E))

ttk.Label(frame, text="Date Greater Than:").grid(row=0, column=0, sticky=tk.W)
date_greater_entry = DateEntry(frame, width=12, date_pattern="yyyy/mm/dd")
date_greater_entry.grid(row=0, column=1, padx=5, pady=5)
two_days_ago = datetime.date.today() - datetime.timedelta(days=2)
date_greater_entry.set_date(two_days_ago)

ttk.Label(frame, text="Date Less Than:").grid(row=1, column=0, sticky=tk.W)
date_less_entry = DateEntry(frame, width=12, date_pattern="yyyy/mm/dd")
date_less_entry.grid(row=1, column=1, padx=5, pady=5)

ttk.Label(frame, text="Search Terms:").grid(row=2, column=0, sticky=tk.NW)
frame_search_terms = ttk.Frame(frame)
frame_search_terms.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
add_search_term_field("9999999")

btn_add_term = ttk.Button(frame, text="Add Search Term", command=lambda: add_search_term_field())
btn_add_term.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

ttk.Label(frame, text="Timeout (seconds):").grid(row=4, column=0, sticky=tk.W)
entry_timeout = ttk.Entry(frame, width=10)
entry_timeout.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)
entry_timeout.insert(0, "30")

btn_run = ttk.Button(frame, text="Run Search", command=start_search, style="GreenButton.TButton")
btn_run.grid(row=5, column=0, columnspan=2, pady=10)

status_var = tk.StringVar()
status_var.set("Status: Idle")
status_label = ttk.Label(frame, textvariable=status_var)
status_label.grid(row=6, column=0, columnspan=2, sticky=tk.W)

progress_bar = ttk.Progressbar(frame, orient='horizontal', mode='determinate', length=200)
progress_bar.grid(row=7, column=0, columnspan=2, pady=5)
progress_bar['maximum'] = 100
progress_bar['value'] = 100

ttk.Label(root, text="Console Output:").grid(row=1, column=0, sticky=tk.W, padx=10)
console_text = ScrolledText(root, width=80, height=20, wrap=tk.WORD, bg="#3e3e3e", fg="white", insertbackground="white")
console_text.grid(row=2, column=0, padx=10, pady=5)

root.after(200, process_log_queue)
root.mainloop()
