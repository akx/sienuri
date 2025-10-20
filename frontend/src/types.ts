export interface TopoPoint {
  lon: number;
  lat: number;
  elevation?: number;
  tpi_20m?: number;
  aspect?: number;
  slope?: number;
}

export interface Bounds {
  west: number;
  south: number;
  east: number;
  north: number;
}

export interface StaticMarker {
  longitude: number;
  latitude: number;
  label?: string;
}

export interface Query {
  name: string;
  getSQL: (bounds: Bounds) => string;
}
