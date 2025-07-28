from __future__ import print_function, unicode_literals
import csv
import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
from sllurp.llrp import LLRPReaderConfig, LLRPReaderClient
from sllurp.log import get_logger


numTags = 0
logger = get_logger(__name__)
csvLogger = None


class CsvLogger(object):
    def __init__(self, filehandle, epc=None, reader_timestamp=False):
        self.rows = []
        self.filehandle = filehandle
        self.num_tags = 0
        self.epc = epc
        self.reader_timestamp = reader_timestamp

    def tag_cb(self, reader, tags):
        host, port = reader.get_peername()
        reader = '{}:{}'.format(host, port)
        logger.info('RO_ACCESS_REPORT from %s', reader)
        for tag in tags:
            epc = tag['EPC']
            if self.epc is not None and epc != self.epc:
                continue
            if self.reader_timestamp:
                timestamp = tag['LastSeenTimestampUTC'] / 1e6
            else:
                timestamp = (datetime.datetime.utcnow() -
                             datetime.datetime(1970, 1, 1)).total_seconds()
            antenna = tag['AntennaID']
            rssi = tag['PeakRSSI']
            self.rows.append((timestamp, reader, antenna, rssi, epc))
            self.num_tags += tag['TagSeenCount']

    def flush(self):
        logger.info('Writing %d rows...', len(self.rows))
        wri = csv.writer(self.filehandle, dialect='excel')
        wri.writerow(('timestamp', 'reader', 'antenna', 'rssi', 'epc'))
        wri.writerows(self.rows)


def finish_cb(reader):
    # Following would be possible, but then concurrent file write would have
    # to be handled. So it is more convenient to do it at the end of main.
    # csvLogger.flush()
    logger.info('Total tags seen: %d', csvLogger.num_tags)


def main(args):
    global csvLogger

    if not args.host:
        logger.info('No readers specified.')
        return 0

    if not args.outfile:
        logger.info('No output file specified.')
        return 0

    enabled_antennas = args.antennas
    if not args.frequencies or args.frequencies == [0]:
        frequency_config = {
            'Automatic': True,
            'ChannelList': [1],
        }
    else:
        frequency_config = {
            'Automatic': False,
            'ChannelList': args.frequencies
        }

    factory_args = dict(
        antennas=enabled_antennas,
        tx_power=args.tx_power,
        start_inventory=True,
        disconnect_when_done=True,
        tag_content_selector={
            'EnableROSpecID': False,
            'EnableSpecIndex': False,
            'EnableInventoryParameterSpecID': False,
            'EnableAntennaID': True,
            'EnableChannelIndex': False,
            'EnablePeakRSSI': True,
            'EnableFirstSeenTimestamp': False,
            'EnableLastSeenTimestamp': True,
            'EnableTagSeenCount': True,
            'EnableAccessSpecID': False,
            'C1G2EPCMemorySelector': {
                'EnableCRC': False,
                'EnablePCBits': False,
            }
        },
        frequencies=frequency_config,
        keepalive_interval=0,
        impinj_extended_configuration=None,
        impinj_search_mode=None,
        impinj_reports=False
    )

    csvLogger = CsvLogger(args.outfile, epc=args.epc,
                          reader_timestamp=args.reader_timestamp)

    reader_clients = []
    for host in args.host:
        if ':' in host:
            host, port = host.split(':', 1)
            port = int(port)
        else:
            port = args.port

        config = LLRPReaderConfig(factory_args)
        reader = LLRPReaderClient(host, port, config)
        reader.add_disconnected_callback(finish_cb)
        reader.add_tag_report_callback(csvLogger.tag_cb)
        reader_clients.append(reader)

    try:
        for reader in reader_clients:
            try:
                reader.connect()
            except Exception as e:
                if "Impinj" in str(e) or "ERROR_MESSAGE" in str(e):
                    logger.warning("Ignoring vendor extension error: %s", e)
                else:
                    raise  # Re-raise if it's another issue
    except Exception as e:
        logger.error("Reader connection failed: %s", e)
        for reader in reader_clients:
            reader.disconnect()

    while True:
        try:
            # Join all threads using a timeout, so it doesn't block
            # Filter out threads which have been joined or are None
            alive_readers = [reader for reader in reader_clients if reader.is_alive()]
            if not alive_readers:
                break
            for reader in alive_readers:
                reader.join(1)
        except (KeyboardInterrupt, SystemExit):
            # catch ctrl-C and stop inventory before disconnecting
            logger.info("Exit detected! Stopping readers...")
            for reader in reader_clients:
                try:
                    reader.disconnect()
                except:
                    logger.exception("Error during disconnect. Ignoring...")

    csvLogger.flush()
    csvLogger.filehandle.close()


def start_logging():
    host_input = host_entry.get()
    host = [h.strip() for h in host_input.split(',')]
    port = int(port_entry.get())
    outfile_path = outfile_entry.get()
    antennas_input = antennas_entry.get()
    antennas = [int(x.strip()) for x in antennas_input.split(',')]
    tx_power = int(tx_power_entry.get())
    epc = epc_entry.get() or None
    reader_timestamp = timestamp_var.get()
    frequencies = []

    if not host or not outfile_path:
        messagebox.showerror("Input Error", "Please fill in all fields.")
        return

    try:
        outfile = open(outfile_path, 'w', newline='')  # ✅ Correct: open file
    except Exception as e:
        messagebox.showerror("File Error", f"Failed to open file: {e}")
        return

    args = type('Args', (object,), {
        'host': host,
        'port': port,
        'outfile': outfile,
        'antennas': antennas,
        'tx_power': tx_power,
        'epc': epc,
        'reader_timestamp': reader_timestamp,
        'frequencies': frequencies
    })

    main(args)


def select_output_file():
    file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    if file_path:
        outfile_entry.delete(0, tk.END)  # Clear existing entry
        outfile_entry.insert(0, file_path)  # Insert selected file path


# GUI Setup
root = tk.Tk()
root.title("RFID Tag Logger")

tk.Label(root, text="Reader Host(s) (comma-separated):").grid(row=0, column=0)
host_entry = tk.Entry(root)
host_entry.grid(row=0, column=1)

tk.Label(root, text="Port:").grid(row=1, column=0)
port_entry = tk.Entry(root)
port_entry.grid(row=1, column=1)

tk.Label(root, text="Output File:").grid(row=2, column=0)
outfile_entry = tk.Entry(root)
outfile_entry.grid(row=2, column=1)

# Button to select output file
select_button = tk.Button(root, text="Select File", command=select_output_file)
select_button.grid(row=2, column=2)

tk.Label(root, text="Antenna IDs (comma-separated):").grid(row=3, column=0)
antennas_entry = tk.Entry(root)
antennas_entry.grid(row=3, column=1)

tk.Label(root, text="Transmission Power:").grid(row=4, column=0)
tx_power_entry = tk.Entry(root)
tx_power_entry.grid(row=4, column=1)

tk.Label(root, text="EPC (optional):").grid(row=5, column=0)
epc_entry = tk.Entry(root)
epc_entry.grid(row=5, column=1)

timestamp_var = tk.BooleanVar()
tk.Checkbutton(root, text="Use Reader Timestamp", variable=timestamp_var).grid(row=6, columnspan=2)

start_button = tk.Button(root, text="Start Logging", command=start_logging)
start_button.grid(row=7, columnspan=2)

if __name__ == "__main__":
    root.mainloop()
