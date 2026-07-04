import { ChefHat, Lightbulb, MapPin, Utensils } from "lucide-react";
import { useChatStore } from "@/store/useChatStore";

export function RightPanel() {
  const messages = useChatStore((state) => state.messages);
  const latestAssistant = [...messages]
    .reverse()
    .find((message) => message.role === "assistant" && message.id !== "welcome" && message.metadata);

  const foods = latestAssistant?.metadata?.foodRecommendations || [];
  const tips = latestAssistant?.metadata?.tips || [];
  const city = latestAssistant?.metadata?.city;
  const hasContent = foods.length > 0 || tips.length > 0;

  return (
    <aside className="hidden w-80 shrink-0 overflow-y-auto border-l border-slate-200 bg-slate-50/70 p-5 xl:block">
      {!hasContent ? (
        <div className="rounded-lg border border-dashed border-slate-200 bg-white p-5">
          <div className="text-sm font-semibold text-slate-900">等待查询结果</div>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            提问后，这里会展示后端真实返回的美食推荐和旅行小贴士。
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {foods.length > 0 && (
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <Utensils className="h-4 w-4 text-emerald-600" />
                  推荐美食
                </h2>
                {city && <span className="text-xs text-slate-400">{city}</span>}
              </div>

              <div className="space-y-3">
                {foods.slice(0, 4).map((food) => (
                  <div key={`${food.name}-${food.area || ""}`} className="flex gap-3 rounded-lg bg-slate-50 p-3">
                    <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                      <ChefHat className="h-4 w-4" />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-semibold text-slate-800">{food.name}</span>
                      {food.area && (
                        <span className="mt-0.5 flex items-center gap-1 text-xs text-slate-500">
                          <MapPin className="h-3 w-3" />
                          {food.area}
                        </span>
                      )}
                      {food.reason && <span className="mt-1 line-clamp-2 block text-xs leading-5 text-slate-500">{food.reason}</span>}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {tips.length > 0 && (
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-900">
                <Lightbulb className="h-4 w-4 text-amber-500" />
                旅行小贴士
              </div>

              <ul className="space-y-3">
                {tips.slice(0, 4).map((tip) => (
                  <li key={`${tip.title}-${tip.content}`} className="rounded-lg bg-slate-50 px-3 py-3">
                    <div className="text-sm font-semibold text-slate-800">{tip.title}</div>
                    <p className="mt-1 text-xs leading-5 text-slate-500">{tip.content}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </aside>
  );
}
