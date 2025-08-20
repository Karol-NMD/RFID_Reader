"use client"

import { useEffect, useState } from "react"
import axios from "axios"

interface TagRead {
  id: number
  epc_hex: string
  epc_ascii: string | null
  antenna: string
  channel: string
  seen_count: string
  last_seen: string
}

export default function Dashboard() {
  const [readerIP, setReaderIP] = useState<string>("")
  const [status, setStatus] = useState<"Disconnected" | "Connected" | "Running">("Disconnected")
  const [tags, setTags] = useState<TagRead[]>([])
  const [error, setError] = useState("")
  const [antennas, setAntennas] = useState<number[]>([])
  const [powerMap, setPowerMap] = useState<{ [key: number]: number }>({})

  // Load saved IP if any
  useEffect(() => {
    const storedIP = localStorage.getItem("rfid_ip")
    if (storedIP) setReaderIP(storedIP)
  }, [])

  // Poll live tags every second
  useEffect(() => {
    const socket = new WebSocket("ws://127.0.0.1:8000/ws/live-tags")

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.tags) {
        setTags(data.tags)
      }
    }

    socket.onerror = () => {
      setError("⚠️ WebSocket error.")
    }

    return () => socket.close()
  }, [])

  const fetchAntennas = async () => {
    const res = await axios.get("http://127.0.0.1:8000/api/antennas")
    const antList = res.data.antennas || []
    setAntennas(antList)
    setPowerMap(Object.fromEntries(antList.map((a: number) => [a, 20]))) // default 20 dBm
  }

  const applyTxPower = async () => {
    await axios.post("http://127.0.0.1:8000/api/set-tx-power", {
      power_map: powerMap,
    })
    alert("✅ Power settings applied.")
  }

  const notify = (msg: string) => alert(msg)

  const pingReader = async () => {
    try {
      const res = await axios.post("http://127.0.0.1:8000/api/ping", { ip: readerIP })
      notify(res.data.message)
    } catch {
      notify("❌ Ping failed")
    }
  }

  const connect = async () => {
    try {
      await axios.post("http://127.0.0.1:8000/api/connect", { ip: readerIP })
      localStorage.setItem("rfid_ip", readerIP)
      setStatus("Connected")
      notify("✅ Connected")
    } catch {
      notify("❌ Connect failed")
    }
  }

  const disconnect = async () => {
    try {
      await axios.post("http://127.0.0.1:8000/api/disconnect")
      localStorage.removeItem("rfid_ip")
      setStatus("Disconnected")
      notify("🔌 Disconnected")
    } catch {
      notify("❌ Disconnect failed")
    }
  }

  const startInventory = async () => {
    try {
      await axios.post("http://127.0.0.1:8000/api/start-inventory", { ip: readerIP })
      setStatus("Running")
      notify("📦 Inventory started")
    } catch {
      notify("❌ Failed to start inventory")
    }
  }

  const stopInventory = async () => {
    try {
      await axios.post("http://127.0.0.1:8000/api/stop-inventory")
      setStatus("Connected")
      notify("🛑 Inventory stopped")
    } catch {
      notify("❌ Failed to stop inventory")
    }
  }

  return (
    <div className="p-4 max-w-6xl mx-auto">
      <h1 className="text-3xl text-blue-600 font-bold">RFID Live Dashboard</h1>
      <p className="text-gray-500 mb-6">View RFID tag read data</p>

      <div className="flex items-center gap-2 mb-4">
        <input
          type="text"
          placeholder="Enter RFID Reader IP (e.g., 192.168.1.100)"
          value={readerIP}
          onChange={(e) => setReaderIP(e.target.value)}
          className="cursor-pointer border-blue-300 text-gray-900 px-4 py-2 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full sm:w-96"
        />

        <div className="flex gap-2 flex-wrap">
          <button onClick={pingReader} className="cursor-pointer bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600 active:scale-95 transition transform duration-100">Ping</button>
          <button onClick={connect} className="cursor-pointer bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 active:scale-95 transition transform duration-100">Connect</button>
          <button onClick={disconnect} className="cursor-pointer bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 active:scale-95 transition transform duration-100">Disconnect</button>
          <button onClick={startInventory} className="cursor-pointer bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 active:scale-95 transition transform duration-100">Start</button>
          <button onClick={stopInventory} className="cursor-pointer bg-gray-700 text-white px-4 py-2 rounded hover:bg-gray-800 active:scale-95 transition transform duration-100">Stop</button>
        </div>

        <div className="text-sm mt-2">
          <span>Status: </span>
          <span className={
            status === "Disconnected" ? "text-red-600" :
              status === "Connected" ? "text-yellow-500" : "text-green-600"
          }>
            {status}
          </span>
        </div>
      </div>

      <h2 className="text-2xl font-semibold mb-2">📦 Live Tag Reads</h2>
      {error && <p className="text-red-500">{error}</p>}

      {tags.length === 0 ? (
        <p className="text-gray-500">No tags yet...</p>
      ) : (
        <div className="overflow-x-auto border rounded max-h-[65vh] overflow-y-auto">
          <table className="min-w-full table-auto text-sm text-gray-800">
            <thead className="bg-gray-100 text-gray-700 sticky top-0">
              <tr>
                <th className="text-left px-4 py-2">EPC_HEX</th>
                <th className="text-left px-4 py-2">EPC_ASCII</th>
                <th className="text-left px-4 py-2">Antenna</th>
                <th className="text-left px-4 py-2">Channel</th>
                <th className="text-left px-4 py-2">Seen Count</th>
                <th className="text-left px-4 py-2">Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {tags.map((tag, i) => (
                <tr key={`${tag.epc_hex}-${i}`} className="border-t hover:bg-gray-50">
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
      <div className="mt-6">
        <button onClick={fetchAntennas} className="cursor-pointer bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 active:scale-95 transition duration-100">
          🔍 Detect Antennas
        </button>

        {antennas.length > 0 && (
          <div className="mt-4 space-y-2">
            {antennas.map((ant) => (
              <div key={ant} className="flex items-center gap-2">
                <label>Antenna {ant} TX Power:</label>
                <input
                  type="number"
                  min="0"
                  max="30"
                  value={powerMap[ant] || ""}
                  onChange={(e) => setPowerMap(prev => ({ ...prev, [ant]: Number(e.target.value) }))}
                  className="cursor-pointer border-blue-300 text-gray-900 px-2 py-1 rounded w-20"
                />
              </div>
            ))}
            <button onClick={applyTxPower} className="mt-2 bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 active:scale-95 transition">
              💡 Apply TX Power
            </button>
          </div>
        )}
      </div>

    </div>

  )
}