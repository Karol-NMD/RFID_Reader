#!/usr/bin/env python

import time
import logging
import threading
import sqlite3
import datetime
from queue import Queue, Empty
from typing import Optional

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
LOG_FILE_PATH = "tag_reads.txt"
DB_FILE = "tags.db"
stop_event = threading.Event()

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
            antenna TEXT,
            channel TEXT,
            seen_count TEXT,
            last_seen TEXT
        )
    ''')
    conn.commit()
    conn.close()


def save_tag_to_db(tag_data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO tag_reads (epc_hex, epc_ascii, antenna, channel, seen_count, last_seen)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        tag_data["epc_hex"],
        tag_data["epc_ascii"],
        str(tag_data["antenna"]),
        str(tag_data["channel"]),
        str(tag_data["seen_count"]),
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
        print(f"ID: {row[0]} | EPC_Hex: {row[1]} | EPC_Ascii: {row[2]} | Antenna: {row[3]} | Channel: {row[4]} "
              f"| Seen: {row[5]} | Time: {row[6]}")


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
            except (UnicodeDecodeError, ValueError):
                epc_real_ascii = None  # Or set to "<non-ascii>"

            last_seen_raw = tag.get("LastSeenTimestampUTC")
            last_seen_str = str(datetime.datetime.fromtimestamp(last_seen_raw / 1_000_000, datetime.UTC).strftime("%Y-%m-%d %H:%M:%S"))


            tag_data = {
                "epc_hex": epc_hex,
                "epc_ascii": epc_real_ascii,
                "antenna": tag.get("AntennaID"),
                "channel": tag.get("ChannelIndex"),
                "seen_count": tag.get("TagSeenCount"),
                "last_seen": last_seen_str
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


# # -------- COMMAND FUNCTIONS -------- #
# def clear_tag_data():
#     print("🧹 Tag data cleared.")


# def start_reading():
#     if READER and READER.is_alive():
#         clear_tag_data()
#         READER.llrp.startInventory()
#         print("📡 Started inventory.")


# def stop_reading():
#     if READER and READER.is_alive():
#         READER.llrp.stopPolitely()
#         print("🛑 Stopped inventory.")


# def print_reader_state():
#     if READER and READER.is_alive():
#         print(f"📊 Reader state: {LLRPReaderState.getStateName(READER.llrp.state)}")
#     else:
#         print("🔌 Reader not connected.")


# -------- THREAD: TAG DISPLAY -------- #
def process_tags_console():
    while not stop_event.is_set():
        try:
            tag = TAG_QUEUE.get(timeout=0.1)
            print(f"\n📦 New tag: {tag}")
            # print(f" - EPC (HEX): {tag['epc_hex']} || EPC (ASCII): {tag['epc_ascii']} | Antenna: {tag['antenna']} | "
            #       f"Ch: {tag['channel']} | Seen: {tag['seen_count']}x | Time: {tag['last_seen']}")
            with open(LOG_FILE_PATH, "a") as f:
                f.write(f"{tag}\n")
            save_tag_to_db(tag)  # Save to SQLite
        except Empty:
            continue
        except Exception as e:
            print(f"❌ Error in tag processing thread: {e}")
        time.sleep(0.05)


# -------- USER INTERFACE LOOP -------- #
# def user_interface():
#     while True:
#         print("\nCommands: [start] [stop] [clear] [state] [view] [exit]")
#         cmd = input(">> ").strip().lower()
#         if cmd == "start":
#             start_reading()
#         elif cmd == "stop":
#             stop_reading()
#         elif cmd == "clear":
#             clear_tag_data()
#         elif cmd == "state":
#             print_reader_state()
#         elif cmd == "view":
#             view_database_contents()
#         elif cmd == "exit":
#             stop_reading()
#             break
#         else:
#             print("❓ Unknown command.")


# -------- MAIN -------- #
def start_inventory_with_ip(ip_address):
    global READER, LOG_FILE_PATH, stop_event

    # Setup SQLite
    init_db()

    stop_event.clear()

    LOG_FILE_PATH = "tag_reads.txt"

    # print("📁 Please choose a file to save tag logs...")
    # log_path = filedialog.asksaveasfilename(
    #     title="Select log file location",
    #     defaultextension=".txt",
    #     filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    # )

    # if log_path:
    #     LOG_FILE_PATH = log_path
    #     print(f"✅ Logging to: {LOG_FILE_PATH}")
    # else:
    #     print("⚠️ No file selected. Using default: tag_reads.txt")

    # reader_ip = input("🔧 Enter RFID reader IP address (e.g., 192.168.1.100): ").strip()
    # if not reader_ip:
    #     print("❌ No IP address entered. Exiting...")
    #     return

    # print("🚀 Initializing RFID Reader...")

    print(f"🔌 Connecting to RFID reader at {ip_address}...")

    # Create configuration with frequent reporting
    config = LLRPReaderConfig()
    config.reset_on_connect = True
    config.start_inventory = True
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
    try:
        READER = LLRPReaderClient(ip_address, PORT, config)
        READER.add_tag_report_callback(tag_report_cb)
        READER.add_event_callback(connection_event_cb)
        READER.connect()
        time.sleep(2)  # Wait for connection to stabilize

        print("✅ Reader connected successfully!")

        # Launch tag processing thread
        tag_thread = threading.Thread(target=process_tags_console, daemon=True)
        tag_thread.start()

        # # Start user loop
        # user_interface()

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

def stop_inventory():
    global READER
    stop_event.set()
    if READER and READER.is_alive():
        try:
            READER.llrp.stop()
            READER.disconnect()
            print("🛑 Inventory stopped and reader disconnected.")
        except Exception as e:
            print(f"⚠️ Error stopping reader: {e}")

#     # Graceful shutdown
#     if READER and READER.is_alive():
#         READER.llrp.stopPolitely()
#         READER.disconnect()
#         print("👋 Reader disconnected. Exiting...")


# if __name__ == "__main__":
#     main()
