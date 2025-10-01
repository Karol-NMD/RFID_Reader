import clr

clr.AddReference("dlls/RFIDReader")
from CS_RFID3_Host_Sample1 import RfidService

svc = RfidService()
svc.Connect("192.168.1.100", 5084)
epcs = svc.ReadEPCs()
tids = svc.ReadTIDs()
print("EPCs:", epcs)
print("TIDs:", tids)
svc.Disconnect()
