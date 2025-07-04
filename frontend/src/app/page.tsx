"use client"

import { useEffect, useState } from "react"
import axios from "axios"

interface TagRead {
  tagId: string
  timestamp: string
  location: string
  reader: string
}

type SortKey = "location" | "timestamp" | "reader" | null

export default function Home() {
  const [tagReads, setTagReads] = useState<TagRead[]>([])
  const [sortKey, setSortKey] = useState<SortKey>(null)
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc")

  useEffect(() => {
    axios.get("https://localhost:8000/api/tag-reads").then((res) => setTagReads(res.data))
  }, [])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"))
    } else {
      setSortKey(key)
      setSortOrder("asc")
    }
  }

  const sortedReads = [...tagReads].sort((a, b) => {
    if (!sortKey) return 0
    const aVal = a[sortKey]
    const bVal = b[sortKey]
    if (sortKey === "timestamp") {
      return sortOrder === "asc"
        ? new Date(aVal).getTime() - new Date(bVal).getTime()
        : new Date(bVal).getTime() - new Date(aVal).getTime()
    }
    return sortOrder === "asc"
      ? String(aVal).localeCompare(String(bVal))
      : String(bVal).localeCompare(String(aVal))
  })

  const handleExport = () => {
    const csvContent = [
      ["Tag ID", "Timestamp", "Location", "Reader"],
      ...tagReads.map(tag => [tag.tagId, tag.timestamp, tag.location, tag.reader])
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
      <h1 className="text-3xl text-blue-600 font-bold">Tag Reads</h1>
      <p className="text-gray-500 mb-6">View and manage RFID tag read data</p>

      <div className="flex justify-between items-center mb-4">
        {/* Left-aligned sort buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => handleSort("location")}
            className="bg-blue-100 text-blue-800 px-4 py-1 rounded"
          >
            Location
          </button>
          <button
            onClick={() => handleSort("timestamp")}
            className="bg-blue-100 text-blue-800 px-4 py-1 rounded"
          >
            Date
          </button>
          <button
            onClick={() => handleSort("reader")}
            className="bg-blue-100 text-blue-800 px-4 py-1 rounded"
          >
            Reader
          </button>
        </div>

        {/* Right-aligned export button */}
        <button
          onClick={handleExport}
          className="bg-gray-100 text-gray-800 font-semibold px-4 py-2 rounded hover:bg-gray-200"
        >
          Export Data
        </button>
      </div>


      <div className="border rounded overflow-hidden">
        <div className="grid grid-cols-4 bg-gray-100 p-2 font-medium text-gray-700">
          <div>Tag ID</div>
          <div>Timestamp</div>
          <div>Location</div>
          <div>Reader</div>
        </div>

        {sortedReads.map((read, idx) => (
          <div
            key={idx}
            className="grid grid-cols-4 border-t p-2 text-sm text-gray-800"
          >
            <div>{read.tagId}</div>
            <div>{new Date(read.timestamp).toLocaleString()}</div>
            <div>{read.location}</div>
            <div>{read.reader}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
