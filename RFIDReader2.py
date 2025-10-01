#!/usr/bin/env python

import time
import logging
import threading
import sqlite3
import datetime
from queue import Queue, Empty
from typing import Optional
import os

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
DB_FILE = "tags_bassa2.db"
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

# -------- THREAD: TAG DISPLAY -------- #
def process_tags_console():
    while not stop_event.is_set():
        try:
            tag = TAG_QUEUE.get(timeout=0.1)
            print(f"\n📦 New tag: {tag}")
            save_tag_to_db(tag)  # Save to SQLite
        except Empty:
            continue
        except Exception as e:
            print(f"❌ Error in tag processing thread: {e}")
        time.sleep(0.05)

def get_reader_antennas():
    global READER
    if not READER:
        return []

    try:
        antennas = READER.llrp.get_antenna_config()
        return list(antennas.keys())
    except Exception as e:
        print(f"⚠️ Failed to get antenna info: {e}")
        return []

def set_tx_power_for_antennas(power_map: dict):
    global READER
    if not READER:
        raise Exception("Reader not connected.")

    try:
        READER.llrp.set_tx_power(power_map)
        return True
    except Exception as e:
        raise Exception(f"Error setting TX power: {e}")

def connect_reader(ip_address):
    global READER, stop_event
    init_db()
    stop_event.clear()
    try:
        config = LLRPReaderConfig()
        config.reset_on_connect = True
        config.start_inventory = False
        config.tx_power = {1: 0, 2: 0, 3: 0, 4: 0}
        config.antennas = [1, 2, 3, 4]
        config.report_every_n_tags = 1  # Report after every tag seen
        config.reader_mode = 'MaxThroughput'  # or a valid string like 'AutoSetDenseReader'
        config.search_mode = 'DualTarget'  # or a mode like 'DualTarget'

        # Configure the fields to include in each tag report
        config.tag_content_selector = {
            'EnableAntennaID': True,
            'EnableChannelIndex': True,
            'EnablePeakRSSI': True,
            'EnableFirstSeenTimestamp': True,
            'EnableLastSeenTimestamp': True,
            'EnableTagSeenCount': True,
            'EnableAccessSpecID': True,
        }

        READER = LLRPReaderClient(ip_address, PORT, config)
        READER.add_tag_report_callback(tag_report_cb)
        READER.add_event_callback(connection_event_cb)
        READER.connect()
        time.sleep(2)
        print("Connected to RFID Reader Successfully")
    except Exception as e:
        print(f"Error connecting reader: {e}")


def disconnect_reader():
    global READER
    stop_event.set()
    if READER and READER.is_alive():
        try:
            READER.disconnect()
            print("Reader Disconnected")
        except Exception as e:
            print(f"Failed to disconnect: {e}")


# -------- MAIN -------- #
def start_inventory_with_ip(ip_address):
    global stop_event

    print(f"🔌 Starting inventory for reader at {ip_address}...")

    # Launch tag processing thread
    tag_thread = threading.Thread(target=process_tags_console, daemon=True)
    tag_thread.start()


def stop_inventory():
    global READER
    stop_event.set()
    if READER and READER.is_alive():
        try:
            READER.llrp.stop()
            print("🛑 Inventory stopped")
        except Exception as e:
            print(f"⚠️ Error stopping reader: {e}")
