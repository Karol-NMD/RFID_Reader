#!/usr/bin/env python

import time
import logging
import threading
import sqlite3
import datetime
from queue import Queue, Empty
from typing import Optional
from collections import deque
import tkinter as tk
from tkinter import filedialog

from sllurp.llrp import (
    LLRP_DEFAULT_PORT,
    LLRPReaderClient,
    LLRPReaderConfig,
    LLRPReaderState,
)

# -------- RFID CONFIGURATION -------- #
PORT = LLRP_DEFAULT_PORT

# -------- GLOBALS -------- #
READER: Optional[LLRPReaderClient] = None
TAG_QUEUE = Queue()
SEEN_TAGS = deque(maxlen=100)  # Keep latest 100 for reference
LOG_FILE_PATH = "tag_reads.txt"
DB_FILE = "tags.db"

# -------- LOGGING SETUP -------- #
logging.basicConfig(level=logging.INFO)
sllurp_logger = logging.getLogger("sllurp")
sllurp_logger.setLevel(logging.INFO)
sllurp_logger.addHandler(logging.StreamHandler())


# -------- DATABASE SETUP -------- #
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tag_reads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            epc_hex TEXT NOT NULL,
            epc_ascii TEXT,
            tid TEXT,
            antenna INTEGER,
            channel INTEGER,
            seen_count INTEGER,
            last_seen TEXT
        )
    ''')
    conn.commit()
    conn.close()


def save_tag_to_db(tag_data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO tag_reads (epc_hex, epc_ascii, tid, antenna, channel, seen_count, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        tag_data["epc_hex"],
        tag_data["epc_ascii"],
        tag_data["tid"],
        tag_data["antenna"],
        tag_data["channel"],
        tag_data["seen_count"],
        tag_data["last_seen"]
    ))
    conn.commit()
    conn.close()


def view_database_contents():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM tag_reads ORDER BY id ASC")  # Remove LIMIT
    rows = c.fetchall()
    conn.close()
    if not rows:
        print("📭 No tags in the database yet.")
        return
    print(f"\n📋 All tags in the database:")
    for row in rows:
        print(f"ID: {row[0]} | EPC_Hex: {row[1]} | EPC_Ascii: {row[2]} | TID: {row[3]} | Ant: {row[4]} | Ch: {row[5]} "
              f"| Seen: {row[6]} | Time: {row[7]}")


# -------- CALLBACKS -------- #
def tag_report_cb(_reader, tag_reports):
    """Callback for tag reads"""
    for tag in tag_reports:
        try:
            epc = tag["EPC"]
            epc_hex = epc.decode("ascii").upper()
            try:
                epc_real_bytes = bytes.fromhex(epc.decode("ascii"))
                epc_real_ascii = epc_real_bytes.decode("ascii")
            except UnicodeDecodeError:
                epc_real_ascii = None  # Or set to "<non-ascii>"

            last_seen_raw = tag.get("LastSeenTimestampUTC")
            last_seen_str = datetime.datetime.utcfromtimestamp(last_seen_raw / 1_000_000).strftime("%Y-%m-%d %H:%M:%S")

            tid_value = None  # The need of a program to fetch this TID

            op_spec_result = tag.get("AccessCommandOpSpecResult")
            if op_spec_result and "C1G2ReadOpSpecResult" in op_spec_result:
                try:
                    tid_bytes = op_spec_result["C1G2ReadOpSpecResult"]["ReadData"]
                    tid_value = tid_bytes.hex().upper()
                except Exception as e:
                    logging.warning(f"Failed to parse TID: {e}")

            tag_data = {
                "epc_hex": epc_hex,
                "epc_ascii": epc_real_ascii,
                "tid": tid_value,
                "channel": tag.get("ChannelIndex"),
                "antenna": tag.get("AntennaID"),
                "last_seen": last_seen_str,
                "seen_count": tag.get("TagSeenCount"),
            }
            TAG_QUEUE.put(tag_data)
        except Exception as e:
            print(f"⚠️ Error parsing tag: {e}")


def connection_event_cb(_reader, event):
    """Callback for connection events only"""
    if "ConnectionAttemptEvent" in event:
        logging.info(f"🔄 Connection Event: {event['ConnectionAttemptEvent']}")
    else:
        logging.info(f"ℹ️ Other Event: {event}")


# -------- COMMAND FUNCTIONS -------- #
def clear_tag_data():
    # SEEN_TAGS.clear()
    print("🧹 Tag data cleared.")


def start_reading():
    if READER and READER.is_alive():
        clear_tag_data()
        READER.llrp.startInventory()
        print("📡 Started inventory.")


def stop_reading():
    if READER and READER.is_alive():
        READER.llrp.stopPolitely()
        print("🛑 Stopped inventory.")


def print_reader_state():
    if READER and READER.is_alive():
        print(f"📊 Reader state: {LLRPReaderState.getStateName(READER.llrp.state)}")
    else:
        print("🔌 Reader not connected.")


# -------- THREAD: TAG DISPLAY -------- #
def process_tags_console():
    # seen_epcs = set()
    while True:
        try:
            # tag = TAG_QUEUE.get(timeout=0.2)
            tag = TAG_QUEUE.get()
            # epc = tag["epc"]
            # if epc not in seen_epcs:
            #     seen_epcs.add(epc)
            # SEEN_TAGS.append(tag)
            print(f"\n📦 New tag:")
            print(f" - EPC (HEX): {tag['epc_hex']} | EPC (ASCII): {tag['epc_ascii']} | TID: {tag['tid']} | "
                  f"Antenna: {tag['antenna']} | Ch: {tag['channel']} | Seen: {tag['seen_count']}x | "
                  f"Time: {tag['last_seen']}")
            with open(LOG_FILE_PATH, "a") as f:
                f.write(f"{tag['last_seen']}, EPC: {tag['epc_hex']} || {tag['epc_ascii']}, TID: {tag['tid']},"
                        f" Antenna: {tag['antenna']},"
                        f" Channel: {tag['channel']}, SeenCount: {tag['seen_count']}\n")
            save_tag_to_db(tag)  # Save to SQLite
        except Empty:
            continue
        except Exception as e:
            print(f"❌ Error in tag processing thread: {e}")
        time.sleep(0.05)


# -------- USER INTERFACE LOOP -------- #
def user_interface():
    while True:
        print("\nCommands: [start] [stop] [clear] [state] [view] [exit]")
        cmd = input(">> ").strip().lower()
        if cmd == "start":
            start_reading()
        elif cmd == "stop":
            stop_reading()
        elif cmd == "clear":
            clear_tag_data()
        elif cmd == "state":
            print_reader_state()
        elif cmd == "view":
            view_database_contents()
        elif cmd == "exit":
            stop_reading()
            break
        else:
            print("❓ Unknown command.")


# -------- MAIN -------- #
def main():
    global READER
    global LOG_FILE_PATH

    # Setup SQLite
    init_db()

    root = tk.Tk()
    root.withdraw()

    print("📁 Please choose a file to save tag logs...")
    log_path = filedialog.asksaveasfilename(
        title="Select log file location",
        defaultextension=".txt",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )

    if log_path:
        LOG_FILE_PATH = log_path
        print(f"✅ Logging to: {LOG_FILE_PATH}")
    else:
        print("⚠️ No file selected. Using default: tag_reads.txt")

    reader_ip = input("🔧 Enter RFID reader IP address (e.g., 192.168.1.100): ").strip()
    if not reader_ip:
        print("❌ No IP address entered. Exiting...")
        return

    print("🚀 Initializing RFID Reader...")

    # Create configuration with frequent reporting
    config = LLRPReaderConfig()
    config.reset_on_connect = False
    config.start_inventory = False
    config.tx_power = {1: 0, 2: 0}
    config.antennas = [1, 2]
    config.report_every_n_tags = 1  # Report after every tag seen
    config.reader_mode = 'MaxThroughput'  # or a valid string like 'AutoSetDenseReader'
    config.search_mode = 'DualTarget'  # or a mode like 'DualTarget'

    # Configure the fields to include in each tag report
    config.tag_content_selector = {
        'EnableROSpecID': False,
        'EnableSpecIndex': False,
        'EnableInventoryParameterSpecID': False,
        'EnableAntennaID': True,
        'EnableChannelIndex': True,
        'EnablePeakRSSI': True,
        'EnableFirstSeenTimestamp': True,
        'EnableLastSeenTimestamp': True,
        'EnableTagSeenCount': True,
        'EnableAccessSpecID': True,
    }

    # Connect and bind callbacks
    READER = LLRPReaderClient(reader_ip, PORT, config)
    READER.add_tag_report_callback(tag_report_cb)
    READER.add_event_callback(connection_event_cb)
    READER.connect()

    def enable_tid_reading(reader_llrp, stopAfterCount=0):
        # Construct the AccessSpec message manually
        def on_access_spec_added(msg):
            logging.info("AccessSpec added response: %s", msg)

        accessStopParam = {
            'AccessSpecStopTriggerType': 1 if stopAfterCount > 0 else 0,
            'OperationCountValue': stopAfterCount,
        }

        access_spec = {
            'AccessSpecID': 123,
            'AntennaID': 0,
            'ProtocolID': 1,
            'CurrentState': False,
            'ROSpecID': 0,
            'AccessSpecStopTrigger': accessStopParam,
            'AccessCommand': {
                'TagSpec': {
                    'MatchType': 1,
                    'MB': 1,
                    'Pointer': 32,
                    'TagMask': b'',
                    'TagData': b'',
                },
                'AccessCommandOpSpecList': [{
                    'OpSpecID': 1,
                    'OpSpec': {
                        'C1G2Read': {
                            'MB': 2,  # ✔️ TID memory bank
                            'WordPointer': 0,
                            'WordCount': 6,
                            'AccessPassword': 0,
                        }
                    }
                }],
            },
            'AccessReportSpec': {
                'AccessReportTrigger': 1,
            },
        }

        reader_llrp.send_ADD_ACCESSSPEC(access_spec, on_access_spec_added)
        reader_llrp.send_ENABLE_ACCESSSPEC({'AccessSpecID': 123})
        logging.info("AccessSpec to read TID has been added and enabled.")

    enable_tid_reading(READER.llrp)

    time.sleep(2)

    print("✅ Reader connected. Ready for commands.")

    # Launch tag processing thread
    tag_thread = threading.Thread(target=process_tags_console, daemon=True)
    tag_thread.start()

    # Start user loop
    user_interface()

    # Graceful shutdown
    if READER and READER.is_alive():
        READER.llrp.stopPolitely()
        READER.disconnect()
        print("👋 Reader disconnected. Exiting...")


if __name__ == "__main__":
    main()
