import { CloudSun, Droplets, Thermometer, Umbrella, Wind } from "lucide-react";
import type { WeatherData } from "@/types/chat";

interface WeatherCardProps {
  data?: WeatherData;
}

export function WeatherCard({ data }: WeatherCardProps) {
  if (!data) return null;

  const temperature = data.temperature ?? data.temp;

  return (
    <div className="mt-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
        <CloudSun className="h-4 w-4 text-blue-600" />
        {data.city || "未知城市"}天气
      </div>
      <div className="grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
        <div className="flex items-center gap-2"><CloudSun className="h-4 w-4" />{data.condition || "天气状况待确认"}</div>
        <div className="flex items-center gap-2"><Thermometer className="h-4 w-4" />{temperature === undefined ? "温度待确认" : `${temperature}°C`}</div>
        <div className="flex items-center gap-2"><Droplets className="h-4 w-4" />{data.humidity === undefined ? "湿度待确认" : `湿度 ${data.humidity}%`}</div>
        <div className="flex items-center gap-2"><Wind className="h-4 w-4" />{data.wind || "风力待确认"}</div>
        <div className="flex items-center gap-2 sm:col-span-2"><Umbrella className="h-4 w-4" />{data.precipitationProbability === undefined ? "降水概率待确认" : `降水概率 ${data.precipitationProbability}%`}</div>
      </div>
    </div>
  );
}
