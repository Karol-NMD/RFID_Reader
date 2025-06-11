from twisted.internet import reactor
from sllurp.llrp import LLRPClientFactory
from binascii import hexlify


def on_tag_report(_, tag_report):  # _ = unused reader
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
    factory = LLRPClientFactory(
        tagReportCallback=on_tag_report,
        startInventory=True,
        txPower=2600,
        antennaIDs=[1, 2],
        readTid=True
    )

    reactor.connectTCP(READER_IP, 5084, factory)
    reactor.run()


if __name__ == '__main__':
    main()
