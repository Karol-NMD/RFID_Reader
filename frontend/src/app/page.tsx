"use client"

import { useEffect, useState } from "react"
import axios from "axios"
import { clearInterval } from "timers"

interface TagRead {
  id: number
  epc_hex: string
  epc_ascii: string | null
  antenna: string
  channel: string
  seen_count: string
  last_seen: string
}

type SortKey = keyof Pick<TagRead, "epc_hex" | "epc_ascii" | "last_seen"> | null

export default function Home() {
  const [readerIP, setReaderIP] = useState<string>("")
  const [connectStatus, setConnectStatus] = useState<boolean>(false)
  const [tagReads, setTagReads] = useState<TagRead[]>([])
  const [sortKey, setSortKey] = useState<SortKey>("last_seen")
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc")
  const [searchTerm, setSearchTerm] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  // Safe localStorage load on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedIP = localStorage.getItem("rfid_ip");
      const connected = localStorage.getItem("rfid_connected") === "true";
      if (storedIP) setReaderIP(storedIP);
      setConnectStatus(connected);
    }
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      axios.get("http://127.0.0.1:8000/api/db-tags")
        .then((res) => {
          const lines = res.data.output
            .trim()
            .split('\n')
            .filter(line => line.startsWith("ID:"))

          const result: TagRead[] = lines.map(line => {
            const obj: any = {}
            const parts = line.split('|').map(p => p.trim())

            parts.forEach(part => {
              const [key, ...valParts] = part.split(':')
              let value = valParts.join(':').trim()

              switch (key.trim()) {
                case "ID":
                  obj.id = Number(value)
                  break
                case "EPC_Hex":
                  obj.epc_hex = value
                  break
                case "EPC_Ascii":
                  obj.epc_ascii = value === 'None' ? null : value
                  break
                case "Antenna":
                  obj.antenna = value
                  break
                case "Channel":
                  obj.channel = value
                  break
                case "Seen":
                  obj.seen_count = value.replace('x', '')
                  break
                case 'Time':
                  obj.last_seen = value
                  break
                default:
                  break
              }
            })

            return obj
          })

          console.log(result);
          setTagReads(result)
        })
        .catch(() => setError("❌ Failed to load tag data."))
        .finally(() => setLoading(false))
    }, 500)

    return () => clearInterval(interval);
  }, [])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"))
    } else {
      setSortKey(key)
      setSortOrder("asc")
    }
  }

  const filteredReads = tagReads.filter(tag =>
    tag.epc_hex.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (tag.epc_ascii?.toLowerCase().includes(searchTerm.toLowerCase()) ?? false)
  )

  const sortedReads = [...filteredReads].sort((a, b) => {
    if (!sortKey) return 0

    const aVal = a[sortKey] ?? ""
    const bVal = b[sortKey] ?? ""


    if (sortKey === "last_seen") {
      return sortOrder === "asc"
        ? new Date(aVal).getTime() - new Date(bVal).getTime()
        : new Date(bVal).getTime() - new Date(aVal).getTime()
    }
    return sortOrder === "asc"
      ? String(aVal).localeCompare(String(bVal))
      : String(bVal).localeCompare(String(aVal))
  })

  const handleConnect = async () => {
    try {
      await axios.post("http://127.0.0.1:8000/api/start-inventory", { ip: readerIP })
      localStorage.setItem("rfid_ip", readerIP)
      localStorage.setItem("rfid_connected", "true")
      setConnectStatus(true)
    } catch (err) {
      alert("❌ Failed to connect to reader.")
    }
  }

  const handleDisconnect = async () => {
    try {
      await axios.post("http://127.0.0.1:8000/api/stop-inventory")
      alert("✅ Inventory stopped successfully.")
    } catch (err) {
      alert("❌ Failed to stop inventory on backend.")
    }
    localStorage.removeItem("rfid_ip")
    localStorage.removeItem("rfid_connected")
    setConnectStatus(false)
  }

  const handleExport = () => {
    const csvContent = [
      ["ID", "EPC_HEX", "EPC_ASCII", "Antenna", "Channel", "Seen Count", "Timestamp"],
      ...tagReads.map(tag => [
        tag.id,
        tag.epc_hex,
        tag.epc_ascii ?? "",
        tag.antenna,
        tag.channel,
        tag.seen_count,
        tag.last_seen,
      ])
    ]
      .map(row => row.join(","))
      .join("\n");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "tag_reads.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-4 max-w-6xl mx-auto">
      <h1 className="text-3xl text-blue-600 font-bold">RFID Tag Reads</h1>
      <p className="text-gray-500 mb-6">View, search, sort, and export RFID tag read data</p>

      <div className="flex items-center gap-2 mb-4">
        <input
          type="text"
          placeholder="Enter RFID Reader IP (e.g., 192.168.1.100)"
          value={readerIP}
          onChange={(e) => setReaderIP(e.target.value)}
          className="border border-blue-300 text-gray-900 px-4 py-2 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full sm:w-96"
        />
        <button onClick={handleConnect} className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
          Connect
        </button>
        <button onClick={handleDisconnect} className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600">
          Disconnect
        </button>
        <p className="text-sm text-green-700">
          {connectStatus ? `Connected to ${readerIP}` : "Not connected"}
        </p>
      </div>


      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        {/* Sort Buttons */}
        <div className="flex gap-2">
          <button onClick={() => handleSort("epc_hex")} className="bg-blue-100 text-blue-800 px-4 py-1 rounded">
            Sort by EPC (HEX)
          </button>
          <button onClick={() => handleSort("epc_ascii")} className="bg-blue-100 text-blue-800 px-4 py-1 rounded">
            Sort by EPC (ASCII)
          </button>
          <button onClick={() => handleSort("last_seen")} className="bg-blue-100 text-blue-800 px-4 py-1 rounded">
            Sort by Time
          </button>
        </div>

        {/* Search */}
        <input
          type="text"
          placeholder="Search EPC or ASCII..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="border border-blue-300 text-gray-900 px-3 py-1 rounded"
        />

        {/* Right-aligned export button */}
        <button onClick={handleExport} className="bg-gray-100 text-gray-800 font-semibold px-4 py-2 rounded hover:bg-gray-200">
          Export CSV
        </button>
      </div>

      {/* Data Output */}
      {loading ? (
        <p className="text-gray-600">Loading...</p>
      ) : error ? (
        <p className="text-red-500">{error}</p>
      ) : (
        <div className="overflow-x-auto border rounded max-h-[80vh] overflow-y-auto">
          <table className="min-w-full table-auto text-sm text-gray-800">
            <thead className="bg-gray-100 text-gray-700">
              <tr>
                <th className="text-left px-4 py-2">ID</th>
                <th className="text-left px-4 py-2">EPC_HEX</th>
                <th className="text-left px-4 py-2">EPC_ASCII</th>
                <th className="text-left px-4 py-2">Antenna</th>
                <th className="text-left px-4 py-2">Channel</th>
                <th className="text-left px-4 py-2">Seen</th>
                <th className="text-left px-4 py-2">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {sortedReads.map((read) => (
                <tr key={read.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-900">{read.id}</td>
                  <td className="px-4 py-2 text-gray-900">{read.epc_hex}</td>
                  <td className="px-4 py-2 text-gray-900">{read.epc_ascii ?? "-"}</td>
                  <td className="px-4 py-2 text-gray-900">{read.antenna}</td>
                  <td className="px-4 py-2 text-gray-900">{read.channel}</td>
                  <td className="px-4 py-2 text-gray-900">{read.seen_count}</td>
                  <td className="px-4 py-2 text-gray-900">{new Date(read.last_seen).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
