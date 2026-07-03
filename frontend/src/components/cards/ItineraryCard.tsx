import { Clock, MapPin } from "lucide-react";
import type { ItineraryDay } from "@/types/chat";

interface ItineraryCardProps {
  itinerary?: ItineraryDay[];
}

export function ItineraryCard({ itinerary = [] }: ItineraryCardProps) {
  if (!itinerary.length) return null;

  return (
    <div className="mt-3 space-y-3">
      {itinerary.map((day) => (
        <section key={day.day} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">{day.day}{day.title ? ` · ${day.title}` : ""}</h3>
          <div className="mt-3 space-y-3">
            {day.stops.map((stop, index) => (
              <div key={`${stop.title}-${index}`} className="rounded-lg bg-slate-50 p-3">
                <div className="flex flex-wrap items-center gap-2 text-sm font-medium text-slate-800">
                  {stop.time && <span className="inline-flex items-center gap-1 text-xs text-slate-500"><Clock className="h-3.5 w-3.5" />{stop.time}</span>}
                  <span>{stop.title}</span>
                </div>
                {stop.location && <div className="mt-1 inline-flex items-center gap-1 text-xs text-slate-500"><MapPin className="h-3.5 w-3.5" />{stop.location}</div>}
                {stop.description && <p className="mt-2 text-sm leading-6 text-slate-600">{stop.description}</p>}
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
