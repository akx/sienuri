import { Layer } from "react-map-gl/maplibre";

export function getAspectLayer() {
  return (
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
  );
}

export function getCircleLayer() {
  return (
    <Layer
      id="points"
      type="circle"
      paint={{
        "circle-radius": [
          "interpolate",
          ["linear"],
          ["zoom"],
          10,
          2,
          14,
          4,
          16,
          6,
          18,
          10,
          20,
          18,
        ],
        "circle-color": [
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
        "circle-opacity": 0.7,
      }}
    />
  );
}

export function getHeatmapLayer() {
  return (
    <Layer
      id="points-heatmap"
      type="heatmap"
      paint={{
        "heatmap-weight": 0.2,
        "heatmap-intensity": 1,
        "heatmap-radius": 15,
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,
          "rgba(33,102,172,0)",
          0.2,
          "rgb(103,169,207)",
          0.4,
          "rgb(209,229,240)",
          0.6,
          "rgb(253,219,199)",
          0.8,
          "rgb(239,138,98)",
          1,
          "rgb(178,24,43)",
        ],
      }}
    />
  );
}
