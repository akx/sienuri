import "maplibre-gl/dist/maplibre-gl.css";

import { useCallback, useMemo, useRef, useState } from "react";
import type { MapRef } from "react-map-gl/maplibre";
import Map, { Layer, Marker, Source } from "react-map-gl/maplibre";
import useSWR from "swr";

const initCoords = {
  longitude: 22.61,
  latitude: 60.36,
  zoom: 12,
};

interface TopoPoint {
  lon: number;
  lat: number;
  elevation: number;
  tpi_20m: number;
  aspect: number;
  slope: number;
}

interface Bounds {
  west: number;
  south: number;
  east: number;
  north: number;
}

interface StaticMarker {
  longitude: number;
  latitude: number;
  label?: string;
}

const staticMarkers: StaticMarker[] = [
  { longitude: 22.599_633, latitude: 60.352_711, label: "Marker 1" },
  { longitude: 22.600_385, latitude: 60.352_808, label: "Marker 1" },
  { longitude: 22.601_878, latitude: 60.353_145, label: "Marker 1" },
];

const fetcher = async (url: string): Promise<TopoPoint[]> => {
  const response = await fetch(url);
  if (!response.ok) throw new Error("Failed to fetch");
  const data: number[][] = await response.json();
  return data.map((row) => ({
    lon: row[0]!,
    lat: row[1]!,
    elevation: row[2]!,
    tpi_20m: row[3]!,
    aspect: row[4]!,
    slope: row[5]!,
  }));
};

export function App() {
  const mapRef = useRef<MapRef>(null);
  const [bounds, setBounds] = useState<Bounds | null>(null);

  const buildQueryUrl = useCallback((bounds: Bounds) => {
    const { west, south, east, north } = bounds;
    const sql = `
      SELECT lon, lat, elevation, tpi_20m, aspect, slope
      FROM topo
      LEFT JOIN stand ON topo.stand_id = stand.global_stand_id
      WHERE tpi_20m < -0.3 AND tpi_20m > -3
        AND elevation > 1
        AND (aspect >= 315 OR aspect <= 45)
        AND slope < 15
        AND lon >= ${west} AND lon <= ${east}
        AND lat >= ${south} AND lat <= ${north}
        AND stand.maintreespecies IN (1,2,8,10,11,12,16,22,23,30)
      ORDER BY RANDOM()
      LIMIT 20000
    `.trim();
    return `/api/query?${new URLSearchParams({ sql })}`;
  }, []);

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
      west: mapBounds.getWest(),
      south: mapBounds.getSouth(),
      east: mapBounds.getEast(),
      north: mapBounds.getNorth(),
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
    <div style={{ width: "100vw", height: "100vh" }}>
      <Map
        ref={mapRef}
        initialViewState={initCoords}
        style={{ width: "100%", height: "100%" }}
        mapStyle="https://tiles.openfreemap.org/styles/dark"
        onLoad={updateBounds}
        onMoveEnd={updateBounds}
      >
        <Source id="topo-points" type="geojson" data={geojson}>
          <Layer
            id="points"
            type="symbol"
            layout={{
              "text-font": ["Noto Sans Regular"],
              "text-field": "↑",
              "text-size": [
                "interpolate",
                ["linear"],
                ["zoom"],
                10,
                ["+", 4, ["*", ["get", "slope"], 0.3]],
                14,
                ["+", 6, ["*", ["get", "slope"], 0.5]],
                16,
                ["+", 8, ["*", ["get", "slope"], 0.8]],
                18,
                ["+", 10, ["*", ["get", "slope"], 1.2]],
                20,
                ["+", 14, ["*", ["get", "slope"], 2]],
              ],
              "text-rotate": ["get", "aspect"],
              "text-allow-overlap": true,
              "text-ignore-placement": true,
            }}
            paint={{
              "text-color": [
                "interpolate",
                ["linear"],
                ["get", "elevation"],
                0,
                "#0000ff",
                20,
                "#00ff00",
                40,
                "#ffff00",
                60,
                "#ff0000",
              ],
              "text-opacity": 1,
              "text-halo-color": "#00000044",
              "text-halo-width": [
                "interpolate",
                ["linear"],
                ["zoom"],
                10,
                0,
                16,
                0,
                20,
                1.5,
              ],
              "text-halo-blur": 1,
            }}
          />
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
    </div>
  );
}
