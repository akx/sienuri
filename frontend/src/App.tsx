import "maplibre-gl/dist/maplibre-gl.css";

import { useAtom } from "jotai";
import { atomWithStorage } from "jotai/utils";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MapRef } from "react-map-gl/maplibre";
import Map, { Marker, Source } from "react-map-gl/maplibre";
import useSWR from "swr";
import darkMapStyle from "./styles/dark.json";
import lightMapStyle from "./styles/light.json";

import { queries } from "./queries.ts";
import { Bounds, StaticMarker, TopoPoint } from "./types.ts";
import {
  getAspectLayer,
  getCircleLayer,
  getHeatmapLayer,
} from "./layerStyles.tsx";
import { StyleSpecification } from "maplibre-gl";

const initCoords = {
  longitude: 22.26,
  latitude: 60.44,
  zoom: 11,
};

const staticMarkers: StaticMarker[] = [
  // Redacted
];

interface QueryResult {
  columns: string[];
  rows: number[][];
}

const fetcher = async (url: string): Promise<TopoPoint[]> => {
  const response = await fetch(url);
  if (!response.ok) throw new Error("Failed to fetch");
  const { rows, columns } = (await response.json()) as QueryResult;
  return rows.map((row) =>
    Object.fromEntries(row.map((value, index) => [columns[index], value])),
  ) as TopoPoint[];
};

const enum LayerStyle {
  Aspect = "aspect",
  Circle = "circle",
  Heatmap = "heatmap",
}

const darkModeAtom = atomWithStorage("darkMode", false, undefined, {
  getOnInit: true,
});

const layerStyleAtom = atomWithStorage(
  "layerStyle",
  LayerStyle.Aspect,
  undefined,
  {
    getOnInit: true,
  },
);

const queryAtom = atomWithStorage("selectedQuery", "", undefined, {
  getOnInit: true,
});

export function App() {
  const mapRef = useRef<MapRef>(null);
  const [bounds, setBounds] = useState<Bounds | null>(null);
  const [darkMode, setDarkMode] = useAtom(darkModeAtom);
  const [selectedQuery, setSelectedQuery] = useAtom(queryAtom);
  const [layerStyle, setLayerStyle] = useAtom(layerStyleAtom);
  const mapStyle = (
    darkMode ? darkMapStyle : lightMapStyle
  ) as StyleSpecification;

  useEffect(() => {
    document.body.classList.toggle("dark", darkMode);
  }, [darkMode]);
  useEffect(() => {
    if (!selectedQuery || !queries.some((q) => q.name === selectedQuery)) {
      console.log("Setting default query:", queries[0]!.name);
      setSelectedQuery(queries[0]!.name);
    }
  }, [selectedQuery, setSelectedQuery]);

  const buildQueryUrl = (bounds: Bounds) => {
    const q = queries.find((query) => query.name === selectedQuery);
    if (q) {
      const sql = q.getSQL(bounds);
      return `/api/query?${new URLSearchParams({ sql })}`;
    }
    console.warn("Selected query not found:", selectedQuery);
    return null;
  };

  const { data: points = [] } = useSWR<TopoPoint[]>(
    bounds ? buildQueryUrl(bounds) : null,
    fetcher,
    { keepPreviousData: true },
  );

  const updateBounds = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;

    const mapBounds = map.getBounds();
    setBounds({
      west: parseFloat(mapBounds.getWest().toFixed(4)),
      south: parseFloat(mapBounds.getSouth().toFixed(4)),
      east: parseFloat(mapBounds.getEast().toFixed(4)),
      north: parseFloat(mapBounds.getNorth().toFixed(4)),
    });
  }, []);

  const geojson = useMemo(
    () =>
      ({
        type: "FeatureCollection",
        features: points.map((point) => ({
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [point.lon, point.lat],
          } satisfies GeoJSON.Point,
          properties: point,
        })),
      }) satisfies GeoJSON.FeatureCollection<GeoJSON.Geometry, TopoPoint>,
    [points],
  );

  return (
    <>
      <Map
        ref={mapRef}
        initialViewState={initCoords}
        style={{ width: "100%", height: "100%" }}
        mapStyle={mapStyle}
        onLoad={updateBounds}
        onMoveEnd={updateBounds}
      >
        <Source id="topo-points" type="geojson" data={geojson}>
          {layerStyle === LayerStyle.Aspect ? getAspectLayer() : null}
          {layerStyle === LayerStyle.Circle ? getCircleLayer() : null}
          {layerStyle === LayerStyle.Heatmap ? getHeatmapLayer() : null}
        </Source>
        {staticMarkers.map((marker, index) => (
          <Marker
            key={index}
            longitude={marker.longitude}
            latitude={marker.latitude}
            anchor="bottom"
          >
            <div
              style={{
                fontSize: "24px",
                cursor: "pointer",
              }}
              title={marker.label}
            >
              📍
            </div>
          </Marker>
        ))}
      </Map>
      <div className="absolute top-2 left-2 bg-white p-2 rounded shadow text-xs dark:bg-gray-800 dark:text-white">
        <label className="flex items-center gap-1">
          <input
            type="checkbox"
            checked={darkMode}
            onChange={(e) => setDarkMode(e.target.checked)}
          />
          Dark
        </label>
        <label className="flex items-center gap-1 mt-2">
          Layer Style:
          <select
            value={layerStyle}
            onChange={(e) => setLayerStyle(e.target.value as LayerStyle)}
            className="border border-gray-300 rounded p-1"
          >
            <option value={LayerStyle.Aspect}>Aspect</option>
            <option value={LayerStyle.Circle}>Circle</option>
            <option value={LayerStyle.Heatmap}>Heatmap</option>
          </select>
        </label>
        <label className="flex items-center gap-1 mt-2">
          Query:
          <select
            value={selectedQuery}
            onChange={(e) => setSelectedQuery(e.target.value)}
            className="border border-gray-300 rounded p-1"
          >
            {queries.map((query) => (
              <option key={query.name} value={query.name}>
                {query.name}
              </option>
            ))}
          </select>
        </label>
        <div className="mt-2">Points: {points.length}</div>
      </div>
    </>
  );
}
