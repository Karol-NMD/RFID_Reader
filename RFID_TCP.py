import paramiko
import tkinter as tk
from tkinter import filedialog

# _______Ask user to choose output file path__________
root = tk.Tk()
root.withdraw()

output_file = filedialog.asksaveasfilename(
    defaultextension=".txt",
    filetypes=[("Text files", "*.txt")],
    title="Save RFID output as..."
)

if not output_file:
    print("No file selected. Exiting.")
    exit(1)

# _____ SSH Config_____
hostname = "10.220.12.61"
username = "admin"
password = "Eneo@1234"
command = "show tags"

# Initialize SSH Client

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname, username=username, password=password)
    print("[INFO] SSH CONNECTION SUCCESSFUL.")

    stdin, stdout, stderr = client.exec_command(command)
    with open(output_file, "w") as f:
        print(f"[INFO] Connected to {hostname}. Output from `{command}`:\n")
        for line in stdout:
            print(line.strip())
            f.write(line)

    error_output = stderr.read().decode()
    if error_output:
        print(f"[ERROR] {error_output}")

except Exception as e:
    print(f"[ERROR] FAILED TO CONNECT: {e}")
    exit(1)

finally:
    client.close()
