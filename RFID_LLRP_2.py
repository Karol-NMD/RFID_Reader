# Minimal example; see sllurp/verb/inventory.py for more.
from sllurp import llrp
from sllurp.llrp import LLRPReaderConfig, LLRPReaderClient, LLRP_DEFAULT_PORT
import logging
logging.getLogger().setLevel(logging.INFO)

host = input("🔧 Enter RFID reader IP address (e.g., 192.168.1.100): ").strip()

def tag_report_cb (reader, tag_reports):
    for tag in tag_reports:
        print('tag: %r' % tag)

config = LLRPReaderConfig()
reader = LLRPReaderClient(host, LLRP_DEFAULT_PORT, config)
reader.add_tag_report_callback(tag_report_cb)

reader.connect()
# We are now connected to the reader and inventory is running.

try:
    # Block forever or until a disconnection of the reader
    reader.join(None)
except (KeyboardInterrupt, SystemExit):
    # catch ctrl-C and stop inventory before disconnecting
    reader.disconnect()