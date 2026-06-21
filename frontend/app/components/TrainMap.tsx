"use client";
import { useEffect, useState, useRef } from "react";

interface Train {
  train_num: string;
  route: string;
  lat: number;
  lon: number;
  status: string;
  delay_min: number;
  host_rr: string;
  speed: number;
}

export default function TrainMap() {
  const mapRef = useRef<any>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const [trains, setTrains] = useState<Train[]>([]);
  const [selected, setSelected] = useState<Train | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  async function fetchTrains() {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/trains/live");
      const data = await res.json();
      const list: Train[] = data.trains || data;
      setTrains(list);
      setLastUpdated(new Date().toLocaleTimeString());
      setLoading(false);
      return list;
    } catch {
      setLoading(false);
      return [];
    }
  }

  function getColor(train: Train) {
    if (train.host_rr === "Amtrak") return "#1D9E75";
    if (train.delay_min === 0) return "#1D9E75";
    if (train.delay_min < 60) return "#EF9F27";
    if (train.delay_min < 180) return "#D85A30";
    return "#E24B4A";
  }

  function updateMarkers(L: any, map: any, list: Train[]) {
    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];
    list.forEach(train => {
      const color = getColor(train);
      const icon = L.divIcon({
        className: "",
        html: `<div style="
          width:28px;height:28px;border-radius:50%;
          background:${color};border:2px solid rgba(255,255,255,0.8);
          display:flex;align-items:center;justify-content:center;
          font-size:8px;font-weight:700;color:white;
          box-shadow:0 2px 8px rgba(0,0,0,0.5);cursor:pointer;
        ">${train.train_num}</div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });
      const marker = L.marker([train.lat, train.lon], { icon });
      marker.on("click", () => setSelected(train));
      marker.addTo(map);
      markersRef.current.push(marker);
    });
  }

  useEffect(() => {
    if (typeof window === "undefined") return;
    import("leaflet").then(L => {
      if (mapInstanceRef.current) return;
      const map = L.map(mapRef.current, {
        center: [39.5, -98.35],
        zoom: 4,
        zoomControl: true,
      });
      L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        { attribution: "© OpenStreetMap © CARTO", maxZoom: 19 }
      ).addTo(map);
      mapInstanceRef.current = map;
      fetchTrains().then(list => updateMarkers(L, map, list));
      const interval = setInterval(async () => {
        const list = await fetchTrains();
        updateMarkers(L, map, list);
      }, 30000);
      return () => clearInterval(interval);
    });
  }, []);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-white">Live Train Map</span>
          <span className="text-xs bg-green-900 text-green-300 px-2 py-0.5 rounded-full animate-pulse">
            Live · refreshes 30s
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-slate-400">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#1D9E75] inline-block"></span>On time</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#EF9F27] inline-block"></span>&lt;60 min late</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#D85A30] inline-block"></span>&lt;3 hrs late</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#E24B4A] inline-block"></span>3+ hrs late</span>
          {lastUpdated && <span>Updated {lastUpdated}</span>}
        </div>
      </div>
      <div className="relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-900 z-10">
            <span className="text-slate-400 text-sm">Loading live train positions...</span>
          </div>
        )}
        <div ref={mapRef} style={{ height: "420px", width: "100%", background: "#0f1117" }} />
      </div>
      {selected && (
        <div className="border-t border-slate-800 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div>
              <div className="text-xs text-slate-400">Train</div>
              <div className="text-sm font-medium text-white">#{selected.train_num} · {selected.route}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Host RR</div>
              <div className="text-sm text-white">{selected.host_rr}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Status</div>
              <div className="text-sm font-medium" style={{ color: getColor(selected) }}>{selected.status}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Delay</div>
              <div className="text-sm text-white">{selected.delay_min} min</div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Speed</div>
              <div className="text-sm text-white">{selected.speed} mph</div>
            </div>
          </div>
          <button onClick={() => setSelected(null)} className="text-slate-400 text-xs hover:text-white">✕ Close</button>
        </div>
      )}
    </div>
  );
}
