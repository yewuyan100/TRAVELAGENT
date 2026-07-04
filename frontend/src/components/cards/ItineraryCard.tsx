import { CalendarDays, Clock, Map, MapPin, Route } from "lucide-react";
import type { ItineraryDay } from "@/types/chat";
import { MapView } from "@/components/cards/MapView";

interface ItineraryCardProps {
  itinerary?: ItineraryDay[];
  city?: string;
}

export function ItineraryCard({ itinerary = [], city }: ItineraryCardProps) {
  if (!itinerary.length) return null;

  const hasCoordinates = itinerary.some((day) =>
    day.stops.some((stop) => (stop.lat ?? stop.latitude) !== undefined && (stop.lng ?? stop.longitude) !== undefined)
  );

  return (
    <section className="mt-4 overflow-hidden rounded-lg border border-emerald-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-emerald-100 bg-emerald-50/70 px-4 py-4">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-emerald-800">
            <Map className="h-4 w-4" />
            行程概览
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {city || "目的地"} · {itinerary.length} 天 · 已按每日主题整理
          </p>
        </div>
        <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-emerald-700 shadow-sm">
          itinerary
        </span>
      </div>

      <div className="grid gap-3 p-4 md:grid-cols-3">
        {itinerary.map((day, index) => (
          <button
            key={day.day}
            type="button"
            className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-left transition hover:border-emerald-300 hover:bg-emerald-50/50"
            onClick={() => window.alert(`${day.day}：${day.title || "今日行程"}，共 ${day.stops.length} 个安排。`)}
          >
            <div className="text-center text-sm font-semibold text-emerald-700">Day {index + 1}</div>
            <div className="mt-1 truncate text-center text-xs text-slate-500">{day.title || day.theme || "弹性安排"}</div>
          </button>
        ))}
      </div>

      <div className="divide-y divide-slate-100 px-4 pb-4">
        {itinerary.map((day, dayIndex) => (
          <div key={`${day.day}-detail`} className="py-4 first:pt-0">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <CalendarDays className="h-4 w-4 text-emerald-600" />
                Day {dayIndex + 1}
                {day.title ? <span className="text-slate-500">· {day.title}</span> : null}
              </h3>
              {day.pace && <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-500">{day.pace}</span>}
            </div>

            <div className="space-y-3">
              {day.stops.map((stop, index) => (
                <div key={`${stop.title}-${index}`} className="grid grid-cols-[32px_1fr] gap-3">
                  <div className="flex flex-col items-center">
                    <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-emerald-50 text-xs font-semibold text-emerald-700">
                      {index + 1}
                    </span>
                    {index < day.stops.length - 1 && <span className="mt-1 h-full w-px bg-emerald-100" />}
                  </div>
                  <div className="rounded-lg bg-slate-50 px-3 py-3">
                    <div className="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-800">
                      {stop.time && (
                        <span className="inline-flex items-center gap-1 text-xs font-normal text-slate-500">
                          <Clock className="h-3.5 w-3.5" />
                          {stop.time}
                        </span>
                      )}
                      <span>{stop.title}</span>
                      {stop.type && <span className="rounded-full bg-white px-2 py-0.5 text-xs font-normal text-slate-500">{stop.type}</span>}
                    </div>
                    {stop.location && (
                      <div className="mt-1 inline-flex items-center gap-1 text-xs text-slate-500">
                        <MapPin className="h-3.5 w-3.5" />
                        {stop.location}
                      </div>
                    )}
                    {stop.description && <p className="mt-2 text-sm leading-6 text-slate-600">{stop.description}</p>}
                  </div>
                </div>
              ))}
            </div>

            {day.routes && day.routes.length > 0 && (
              <div className="mt-3 space-y-2 text-xs text-slate-600">
                {day.routes.map((route, index) => (
                  <div key={`${route.from}-${route.to}-${index}`} className="flex flex-wrap items-center gap-2 rounded-lg bg-sky-50 px-3 py-2 text-sky-800">
                    <Route className="h-3.5 w-3.5" />
                    <span>{route.from} → {route.to}</span>
                    {route.distance_m !== undefined && <span>{route.distance_m} 米</span>}
                    {route.duration_min !== undefined && <span>约 {route.duration_min} 分钟</span>}
                  </div>
                ))}
              </div>
            )}

            {day.notes && <p className="mt-3 text-xs leading-5 text-slate-500">{day.notes}</p>}
          </div>
        ))}
      </div>

      {hasCoordinates && (
        <div className="border-t border-slate-100 p-4">
          <MapView
            city={city}
            spots={itinerary.flatMap((day) =>
              day.stops.map((stop) => ({
                name: stop.title,
                lat: stop.lat ?? stop.latitude,
                lng: stop.lng ?? stop.longitude,
                address: stop.address || stop.location,
              }))
            )}
            routes={itinerary.flatMap((day) => day.routes || [])}
            height={280}
          />
        </div>
      )}
    </section>
  );
}
