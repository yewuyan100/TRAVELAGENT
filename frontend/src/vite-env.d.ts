/// <reference types="vite/client" />

declare global {
  interface Window {
    _AMapSecurityConfig?: {
      securityJsCode?: string;
    };
  }

  namespace AMap {
    type LngLatLike = [number, number];

    class Map {
      constructor(container: HTMLElement | string, options?: Record<string, unknown>);
      addControl(control: unknown): void;
      setFitView(overlays?: unknown[], immediately?: boolean, avoid?: number[]): void;
      destroy(): void;
    }

    class Marker {
      constructor(options?: Record<string, unknown>);
      on(event: string, handler: () => void): void;
      setMap(map: Map | null): void;
    }

    class Polyline {
      constructor(options?: Record<string, unknown>);
      setMap(map: Map | null): void;
    }

    class InfoWindow {
      constructor(options?: Record<string, unknown>);
      open(map: Map, position: LngLatLike): void;
    }

    class Pixel {
      constructor(x: number, y: number);
    }

    class Scale {
      constructor(options?: Record<string, unknown>);
    }

    class ToolBar {
      constructor(options?: Record<string, unknown>);
    }
  }
}

export {};
