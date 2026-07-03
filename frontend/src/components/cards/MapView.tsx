import { useEffect, useMemo, useRef, useState } from "react";
import AMapLoader from "@amap/amap-jsapi-loader";
import "./MapView.css";

export interface MapSpot {
  name: string;
  lat?: number;
  lng?: number;
  latitude?: number;
  longitude?: number;
  address?: string;
}

export interface MapRoute {
  from?: string;
  to?: string;
  path?: Array<[number, number]>;
  distance_m?: number;
  duration_min?: number;
  mode?: string;
}

interface MapViewProps {
  spots: MapSpot[];
  routes?: MapRoute[];
  city?: string;
  height?: number | string;
}

interface NormalizedSpot {
  name: string;
  lat: number;
  lng: number;
  address?: string;
}

function normalizeNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }
  return undefined;
}

function normalizeSpot(spot: MapSpot): NormalizedSpot | null {
  const lat = normalizeNumber(spot.lat ?? spot.latitude);
  const lng = normalizeNumber(spot.lng ?? spot.longitude);
  if (lat === undefined || lng === undefined) return null;
  return {
    name: spot.name || "未命名景点",
    lat,
    lng,
    address: spot.address,
  };
}

function normalizePath(path?: Array<[number, number]>): Array<[number, number]> {
  if (!Array.isArray(path)) return [];
  return path
    .map((point) => {
      if (!Array.isArray(point) || point.length < 2) return null;
      const lng = normalizeNumber(point[0]);
      const lat = normalizeNumber(point[1]);
      if (lng === undefined || lat === undefined) return null;
      return [lng, lat] as [number, number];
    })
    .filter((point): point is [number, number] => Boolean(point));
}

function heightStyle(height: number | string): string {
  return typeof height === "number" ? `${height}px` : height;
}

export function MapView({ spots, routes = [], city, height = 360 }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<AMap.Map | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const key = import.meta.env.VITE_AMAP_JS_KEY;
  const securityCode = import.meta.env.VITE_AMAP_SECURITY_CODE;
  const normalizedSpots = useMemo(() => spots.map(normalizeSpot).filter((spot): spot is NormalizedSpot => Boolean(spot)), [spots]);
  const routePaths = useMemo(() => routes.map((route) => normalizePath(route.path)).filter((path) => path.length >= 2), [routes]);

  useEffect(() => {
    if (!key) {
      setStatus("未配置地图 JS API Key，当前仅展示文字行程。");
      return;
    }
    if (!containerRef.current) return;
    if (!normalizedSpots.length) {
      setStatus("当前行程没有可用于地图展示的经纬度，已降级为文字行程。");
      return;
    }

    let cancelled = false;
    let map: AMap.Map | null = null;
    const overlays: Array<AMap.Marker | AMap.Polyline> = [];

    if (securityCode) {
      window._AMapSecurityConfig = { securityJsCode: securityCode };
    }

    setStatus("地图加载中...");

    AMapLoader.load({
      key,
      version: "2.0",
      plugins: ["AMap.Scale", "AMap.ToolBar", "AMap.Driving", "AMap.Walking"],
    })
      .then((AMap) => {
        if (cancelled || !containerRef.current) return;
        const currentMap = new AMap.Map(containerRef.current, {
          zoom: 12,
          viewMode: "2D",
          city,
        });
        map = currentMap;
        mapRef.current = map;

        currentMap.addControl(new AMap.Scale());
        currentMap.addControl(new AMap.ToolBar({ position: { right: "12px", top: "12px" } }));

        normalizedSpots.forEach((spot, index) => {
          const marker = new AMap.Marker({
            position: [spot.lng, spot.lat],
            title: spot.name,
            label: {
              content: `<div class="travel-map-marker-label">${index + 1}</div>`,
              direction: "top",
            },
          });
          const infoWindow = new AMap.InfoWindow({
            content: `<div class="travel-map-info"><strong>${spot.name}</strong>${spot.address ? `<br/>${spot.address}` : ""}</div>`,
            offset: new AMap.Pixel(0, -28),
          });
          marker.on("click", () => infoWindow.open(currentMap, [spot.lng, spot.lat]));
          marker.setMap(currentMap);
          overlays.push(marker);
        });

        const explicitPaths = routePaths.length > 0 ? routePaths : [normalizedSpots.map((spot) => [spot.lng, spot.lat] as [number, number])];
        explicitPaths
          .filter((path) => path.length >= 2)
          .forEach((path) => {
            const polyline = new AMap.Polyline({
              path,
              strokeColor: "#2563eb",
              strokeOpacity: 0.88,
              strokeWeight: 5,
              strokeStyle: "solid",
              lineJoin: "round",
            });
            polyline.setMap(currentMap);
            overlays.push(polyline);
          });

        currentMap.setFitView(overlays, false, [48, 48, 48, 48]);
        setStatus(null);
      })
      .catch((error) => {
        console.error("[MapView] 高德地图加载失败", error);
        setStatus("地图加载失败，当前仅展示文字行程。");
      });

    return () => {
      cancelled = true;
      overlays.forEach((overlay) => overlay.setMap(null));
      if (mapRef.current) {
        mapRef.current.destroy();
        mapRef.current = null;
      }
      map = null;
    };
  }, [city, key, normalizedSpots, routePaths, securityCode]);

  if (!key || !normalizedSpots.length) {
    return <div className="travel-map-fallback">{status || "当前仅展示文字行程。"}</div>;
  }

  return (
    <div className="travel-map-shell" style={{ height: heightStyle(height) }}>
      <div ref={containerRef} className="travel-map-container" />
      {status && <div className="travel-map-status">{status}</div>}
    </div>
  );
}
