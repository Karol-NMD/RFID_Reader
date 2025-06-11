from twisted.internet import reactor, defer
from sllurp.llrp import LLRPClientFactory
from binascii import hexlify


def on_tag_report(_, tag_report):
    for tag in tag_report.msgdict['TagReportData']:
        epc = hexlify(tag.get('EPC-96', b'')).decode()
        antenna = tag.get('AntennaID', 'N/A')
        rssi = tag.get('PeakRSSI', 'N/A')
        tid = None

        for result in tag.get('AccessCommandOpSpecResult', []):
            if result.get('OpSpecResultType') == 'Read':
                tid_bytes = result.get('ReadData', b'')
                if tid_bytes:
                    tid = hexlify(tid_bytes).decode()

        print(f"📡 EPC: {epc} | Antenna: {antenna} | RSSI: {rssi} | TID: {tid or 'N/A'}")


def main():
    READER_IP = '10.220.12.61'
    READER_PORT = 5084

    factory = LLRPClientFactory()
    factory.add_on_tag_report_callback(on_tag_report)

    def on_connect(proto):
        print('✅ Connected to RFID reader.')
        # Set up AccessSpec to read TID
        proto.addAccessSpec({
            'ROSpecID': 0,
            'AccessSpecID': 23,
            'AntennaID': 0,
            'ProtocolID': 1,  # EPCGlobalClass1Gen2
            'AccessSpecStopTrigger': {
                'AccessSpecStopTrigger': 0,
                'OperationCountValue': 0,
            },
            'AccessCommand': {
                'AirProtocolTagSpec': {
                    'C1G2TargetTag': {
                        'MemoryBank': 1,
                        'Pointer': 0,
                        'TagMask': b'',
                        'TagData': b'',
                        'Match': False,
                    },
                },
                'OpSpec': [
                    {
                        'OpSpecID': 1,
                        'OpSpecType': 'C1G2Read',
                        'AccessPassword': 0,
                        'MB': 2,  # TID memory bank
                        'WordPointer': 0,
                        'WordCount': 6,
                    }
                ],
            },
            'AccessPermission': 0,
            'AccessCurrentState': 0,
            'ROSpecIDIsZero': False,
        })

        proto.start()
        print("🚀 Inventory started...")

    factory.add_on_connected_callback(on_connect)

    reactor.connectTCP(READER_IP, READER_PORT, factory)
    reactor.run()


if __name__ == '__main__':
    main()
