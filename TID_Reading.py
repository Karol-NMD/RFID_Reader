from sllurp.llrp import LLRPReaderClient, C1G2Read
import logging
import time

logging.basicConfig(level=logging.DEBUG)

READER_IP = '10.220.12.61'
reader = LLRPReaderClient(READER_IP)

# --- Callback to display EPC and TID ---
def handle_tag_report(_, tag_report_data):
    for tag in tag_report_data:
        epc = tag.get('EPC-96') or tag.get('EPCData')
        tid = None
        for result in tag.get('AccessCommandOpSpecResult', []):
            read_result = result.get('C1G2ReadOpSpecResult')
            if read_result:
                tid = read_result.get('ReadData')
        print(f"EPC: {epc}, TID: {tid}")

reader.add_tag_report_callback(handle_tag_report)
reader.connect()

# --- Full AccessSpec dict (required for v2.0.1) ---
access_spec = {
    'AccessSpecID': 1,
    'AntennaID': 0,
    'ProtocolID': 1,
    'CurrentState': False,
    'ROSpecID': 0,
    'AccessSpecStopTrigger': {
        'AccessSpecStopTriggerType': 0,
        'OperationCountValue': 0
    },
    'AccessCommand': {
        'TagSpecParameter': {
            'C1G2TagSpec': {
                'C1G2TargetTag': []
            }
        },
        'OpSpecParameter': [
            {
                'C1G2Read': {
                    'OpSpecID': 1,
                    'AccessPassword': 0x00000000,
                    'MB': 2,
                    'WordPtr': 0,
                    'WordCount': 6
                }
            }
        ]
    },
    'AccessReportSpec': {
        'AccessReportTrigger': 1
    }
}

# Add and enable AccessSpec
reader.llrp.send_ADD_ACCESSSPEC(access_spec, onCompletion=lambda *_: None)
reader.llrp.send_ENABLE_ACCESSSPEC(None, 1, onCompletion=lambda *_: None)

# --- Keep script running ---
try:
    while reader.is_alive():
        time.sleep(0.1)
except KeyboardInterrupt:
    reader.disconnect()

