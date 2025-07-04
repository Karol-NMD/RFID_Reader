#!/usr/bin/env python

import sllurp.llrp
import sllurp.llrp_proto
import logging
import sys

logging.basicConfig(level=logging.INFO)

# Replace with your reader's IP address
READER_IP = '10.220.12.61'

def on_report(reader, tags):
    for tag in tags:
        epc = tag.get('epc', b'').hex()
        tid = tag.get('tid', b'').hex()  # Get the TID field if present
        print(f'[TAG READ] EPC: {epc} | TID: {tid if tid else "N/A"}')

def main():
    factory = sllurp.llrp.LLRPClientFactory(
        tag_report_callback=on_report,
        tx_power=30,  # Optional: max tx power
        antenna_configuration={
            1: {
                'transmitPower': 30,
                'modeIndex': 1002,
                'session': 2,
                'target': 0,
            }
        }
    )

    # Add an RO Spec that includes TID reading
    # Memory bank 2 is TID
    factory.addROSpec({
        'AISpec': {
            'InventoryParameterSpec': {
                'InventoryParameterSpecID': 1,
                'ProtocolID': sllurp.llrp.LLRP_C1G2,
                'C1G2InventoryCommand': {
                    'TagInventoryStateAware': False,
                    'C1G2Filter': [],
                    'C1G2TagInventoryMask': [],
                    'C1G2TagInventoryStateAwareSingulationControl': {
                        'Session': 2,
                        'TagPopulation': 32,
                        'TagTransitTime': 0,
                    },
                    'C1G2TagInventoryCommandOpSpec': [
                        {
                            'OpSpecID': 1,
                            'AccessCommand': {
                                'AccessSpecID': 1,
                                'MemoryBank': 2,  # TID memory bank
                                'WordPointer': 0,
                                'WordCount': 4,  # Read 4 words = 8 bytes
                                'AccessPassword': 0,
                            }
                        }
                    ]
                }
            }
        }
    })

    # Start connection
    reactor = sllurp.llrp.reactor
    d = factory.connect(READER_IP)

    def fail(f):
        print(f"[ERROR] {f}")
        reactor.stop()

    d.addErrback(fail)
    reactor.run()

if __name__ == '__main__':
    main()
