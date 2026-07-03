import { Clock, MapPin, Route } from "lucide-react";
import type { ItineraryDay } from "@/types/chat";
import { MapView } from "@/components/cards/MapView";

interface ItineraryCardProps {
  itinerary?: ItineraryDay[];
}

export function ItineraryCard({ itinerary = [] }: ItineraryCardProps) {
  if (!itinerary.length) return null;

  return (
    <div className="mt-3 space-y-3">
      {itinerary.map((day) => (
        <section key={day.day} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-900">{day.day}{day.title ? ` · ${day.title}` : ""}</h3>
            {day.pace && <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-500">{day.pace}</span>}
          </div>
          <div className="mt-3 space-y-3">
            {day.stops.map((stop, index) => (
              <div key={`${stop.title}-${index}`} className="rounded-lg bg-slate-50 p-3">
                <div className="flex flex-wrap items-center gap-2 text-sm font-medium text-slate-800">
                  {stop.time && <span className="inline-flex items-center gap-1 text-xs text-slate-500"><Clock className="h-3.5 w-3.5" />{stop.time}</span>}
                  <span>{stop.title}</span>
                  {stop.type && <span className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-500">{stop.type}</span>}
                </div>
                {stop.location && <div className="mt-1 inline-flex items-center gap-1 text-xs text-slate-500"><MapPin className="h-3.5 w-3.5" />{stop.location}</div>}
                {stop.lat !== undefined && stop.lng !== undefined && (
                  <div className="mt-1 inline-flex items-center gap-1 text-xs text-slate-500"><MapPin className="h-3.5 w-3.5" />{stop.lat.toFixed(4)}, {stop.lng.toFixed(4)}</div>
                )}
                {stop.description && <p className="mt-2 text-sm leading-6 text-slate-600">{stop.description}</p>}
              </div>
            ))}
          </div>
          {day.routes && day.routes.length > 0 && (
            <div className="mt-3 space-y-2 border-t border-slate-100 pt-3 text-xs text-slate-600">
              {day.routes.map((route, index) => (
                <div key={`${route.from}-${route.to}-${index}`} className="flex flex-wrap items-center gap-2 rounded-lg bg-blue-50 px-3 py-2 text-blue-800">
                  <Route className="h-3.5 w-3.5" />
                  <span>{route.from} → {route.to}</span>
                  {route.distance_m !== undefined && <span>{route.distance_m} 米</span>}
                  {route.duration_min !== undefined && <span>约 {route.duration_min} 分钟</span>}
                  {route.mode && <span>{route.mode}</span>}
                </div>
              ))}
            </div>
          )}
          {day.notes && <p className="mt-3 text-xs leading-5 text-slate-500">{day.notes}</p>}
          <MapView
            city={day.title}
            spots={day.stops.map((stop) => ({
              name: stop.title,
              lat: stop.lat ?? stop.latitude,
              lng: stop.lng ?? stop.longitude,
              address: stop.address || stop.location,
            }))}
            routes={day.routes}
            height={320}
          />
        </section>
      ))}
    </div>
  );
}
