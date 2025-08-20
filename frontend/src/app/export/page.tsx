// pages/export.tsx
"use client"

import { useEffect, useState } from "react"
import axios from "axios"

interface TagRow {
  id: number
  epc_hex: string
  epc_ascii: string | null
  antenna: string
  channel: string
  seen_count: string
  last_seen: string
}

export default function Export() {
  const [date, setDate] = useState("")
  const [startTime, setStartTime] = useState("")
  const [endTime, setEndTime] = useState("")
  const [dbFile, setDbFile] = useState("")
  const [dbList, setDbList] = useState<string[]>([])
  const [data, setData] = useState<TagRow[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    axios.get("http://127.0.0.1:8000/api/list-dbs")
      .then((res) => {
        if (res.data.databases) {
          setDbList(res.data.databases)
          if (!dbFile && res.data.databases.length > 0) {
            setDbFile(res.data.databases[0])
          }
        }
      })
      .catch(() => alert("❌ Failed to load database files"))
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await axios.get("http://127.0.0.1:8000/api/db-tags", {
        params: {
          date,
          start_time: startTime,
          end_time: endTime,
          db: dbFile,
        },
      })
      setData(res.data.rows || [])
    } catch {
      alert("❌ Failed to load filtered data.")
    } finally {
      setLoading(false)
    }
  }

  const exportCSV = () => {
    const csv = [
      ["ID", "EPC_HEX", "EPC_ASCII", "Antenna", "Channel", "Seen Count", "Last Seen"],
      ...data.map(tag => [
        tag.id,
        tag.epc_hex,
        tag.epc_ascii ?? "",
        tag.antenna,
        tag.channel,
        tag.seen_count,
        tag.last_seen,
      ]),
    ].map(row => row.join(",")).join("\n")

    const blob = new Blob([csv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = "filtered_tags.csv"
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold text-blue-700 mb-4">📁 Export RFID Tag Reads</h1>

      <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="cursor-pointer border px-4 py-2 rounded"
        />
        <input
          type="time"
          value={startTime}
          onChange={(e) => setStartTime(e.target.value)}
          className="cursor-pointer border border-blue-300 text-gray-900 px-4 py-2 rounded"
        />
        <input
          type="time"
          value={endTime}
          onChange={(e) => setEndTime(e.target.value)}
          className="cursor-pointer border border-blue-300 text-gray-900 px-4 py-2 rounded"
        />
        <select
          value={dbFile}
          onChange={(e) => setDbFile(e.target.value)}
          className="cursor-pointer border border-blue-300 text-gray-900 px-4 py-2 rounded"
        >
           {dbList.map(db => (
            <option key={db} value={db}>{db}</option>
          ))}
        </select>
      </div>

      <div className="flex gap-2 mb-4">
        <button onClick={loadData} className="bg-blue-600 text-white px-4 py-2 rounded">Load Data</button>
        <button onClick={exportCSV} className="bg-gray-700 text-white px-4 py-2 rounded">Export CSV</button>
      </div>

      {loading ? (
        <p className="text-gray-600">Loading...</p>
      ) : data.length === 0 ? (
        <p className="text-gray-500">No data to display.</p>
      ) : (
        <div className="overflow-x-auto border rounded max-h-[70vh] overflow-y-auto">
          <table className="min-w-full table-auto text-sm text-gray-800">
            <thead className="bg-gray-100 text-gray-700 sticky top-0">
              <tr>
                <th className="px-4 py-2 text-left">ID</th>
                <th className="px-4 py-2 text-left">EPC_HEX</th>
                <th className="px-4 py-2 text-left">EPC_ASCII</th>
                <th className="px-4 py-2 text-left">Antenna</th>
                <th className="px-4 py-2 text-left">Channel</th>
                <th className="px-4 py-2 text-left">Seen Count</th>
                <th className="px-4 py-2 text-left">Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {data.map(tag => (
                <tr key={tag.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-2">{tag.id}</td>
                  <td className="px-4 py-2">{tag.epc_hex}</td>
                  <td className="px-4 py-2">{tag.epc_ascii ?? "-"}</td>
                  <td className="px-4 py-2">{tag.antenna}</td>
                  <td className="px-4 py-2">{tag.channel}</td>
                  <td className="px-4 py-2">{tag.seen_count}</td>
                  <td className="px-4 py-2">{new Date(tag.last_seen).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
