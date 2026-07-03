import { CloudSun, Droplets, Thermometer, Umbrella, Wind } from "lucide-react";
import type { WeatherData } from "@/types/chat";

interface WeatherCardProps {
  data?: WeatherData;
}

export function WeatherCard({ data }: WeatherCardProps) {
  if (!data) return null;

  const currentTemperature = data.current_temperature ?? data.temperature ?? data.temp;
  const rainProbability = data.rain_probability ?? data.precipitationProbability;

  return (
    <div className="mt-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm font-semibold text-slate-900">
        <span className="inline-flex items-center gap-2">
          <CloudSun className="h-4 w-4 text-blue-600" />
          {data.city || "未知城市"}天气
        </span>
        <span className="text-xs font-normal text-slate-500">
          {[data.provider, data.date].filter(Boolean).join(" · ")}
        </span>
      </div>
      <div className="grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
        <div className="flex items-center gap-2"><CloudSun className="h-4 w-4" />{data.condition || "天气状况待确认"}</div>
        <div className="flex items-center gap-2"><Thermometer className="h-4 w-4" />{currentTemperature === undefined ? "当前温度待确认" : `当前 ${currentTemperature}°C`}</div>
        <div className="flex items-center gap-2"><Thermometer className="h-4 w-4" />{data.temp_min === undefined || data.temp_max === undefined ? "最高/最低温待确认" : `${data.temp_min}°C - ${data.temp_max}°C`}</div>
        <div className="flex items-center gap-2"><Wind className="h-4 w-4" />{data.wind || "风力待确认"}</div>
        <div className="flex items-center gap-2 sm:col-span-2"><Droplets className="h-4 w-4" />{rainProbability === undefined ? "降水概率待确认" : `降水概率 ${rainProbability}%`}</div>
        {data.travel_advice && <div className="flex items-start gap-2 sm:col-span-2"><Umbrella className="mt-1 h-4 w-4" /><span>{data.travel_advice}</span></div>}
      </div>
      {data.forecast && data.forecast.length > 1 && (
        <div className="mt-3 grid gap-2 border-t border-slate-100 pt-3 text-xs text-slate-500 sm:grid-cols-3">
          {data.forecast.slice(0, 7).map((item) => (
            <div key={item.date} className="rounded-lg bg-slate-50 p-2">
              <div className="font-medium text-slate-700">{item.date}</div>
              <div>{item.condition || "天气待确认"}</div>
              <div>{item.temp_min ?? "?"}°C - {item.temp_max ?? "?"}°C</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
