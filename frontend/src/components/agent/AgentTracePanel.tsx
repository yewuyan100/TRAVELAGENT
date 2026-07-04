import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import type { MessageMetadata } from "@/types/chat";

interface AgentTracePanelProps {
  metadata?: MessageMetadata;
}

function scoreText(score?: number) {
  return typeof score === "number" ? score.toFixed(2) : "N/A";
}

function boolText(value: unknown) {
  return value ? "是" : "否";
}

export function AgentTracePanel({ metadata }: AgentTracePanelProps) {
  const taskPlan = metadata?.taskPlan || [];
  const toolsUsed = metadata?.toolsUsed || [];
  const chunks = metadata?.retrievedChunks || [];
  const trace = metadata?.traceMetadata || {};
  const hasTrace = metadata?.intent || taskPlan.length || toolsUsed.length || chunks.length;

  if (!hasTrace) return null;

  return (
    <Accordion type="single" collapsible className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3">
      <AccordionItem value="agent-trace" className="border-0">
        <AccordionTrigger className="text-sm font-semibold text-slate-800">
          Agent Trace
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-4 pb-3 text-xs text-slate-600">
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="rounded-md bg-white p-3">
                <div className="font-semibold text-slate-900">Intent</div>
                <div className="mt-1">{String(metadata?.intent || "unknown")}</div>
              </div>
              <div className="rounded-md bg-white p-3">
                <div className="font-semibold text-slate-900">Rerank / Fallback</div>
                <div className="mt-1">
                  Rerank 开启：{boolText(trace.rerank_enabled)}，已使用：{boolText(trace.rerank_used)}，Fallback：{boolText(trace.fallback_used)}
                </div>
              </div>
            </div>

            {taskPlan.length > 0 && (
              <section>
                <div className="mb-2 font-semibold text-slate-900">Task Plan</div>
                <div className="space-y-2">
                  {taskPlan.map((step, index) => (
                    <div key={`${step.step}-${index}`} className="rounded-md bg-white p-3">
                      <div className="font-medium text-slate-900">{index + 1}. {step.step}</div>
                      <div className="mt-1">工具：{step.tool}</div>
                      <div className="mt-1 leading-5">{step.reason}</div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {toolsUsed.length > 0 && (
              <section>
                <div className="mb-2 font-semibold text-slate-900">Tools Used</div>
                <div className="space-y-2">
                  {toolsUsed.map((tool, index) => (
                    <div key={`${tool.tool}-${index}`} className="rounded-md bg-white p-3">
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium text-slate-900">{tool.tool}</span>
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">{tool.status}</span>
                      </div>
                      <div className="mt-1 leading-5">{tool.summary}</div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {chunks.length > 0 && (
              <section>
                <div className="mb-2 font-semibold text-slate-900">Retrieved Knowledge</div>
                <div className="space-y-2">
                  {chunks.map((chunk, index) => (
                    <div key={`${chunk.chunk_id || chunk.title}-${index}`} className="rounded-md bg-white p-3">
                      <div className="font-medium text-slate-900">{chunk.title || "本地知识片段"}</div>
                      <div className="mt-1 flex flex-wrap gap-2 text-slate-500">
                        {chunk.city && <span>{chunk.city}</span>}
                        {chunk.category && <span>{chunk.category}</span>}
                        <span>score {scoreText(chunk.score)}</span>
                      </div>
                      {chunk.content_preview && <p className="mt-2 line-clamp-3 leading-5">{chunk.content_preview}</p>}
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
