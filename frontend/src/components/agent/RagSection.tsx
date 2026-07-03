import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import type { RagSource } from "@/types/chat";

interface RagSectionProps {
  sources?: RagSource[];
}

export function RagSection({ sources = [] }: RagSectionProps) {
  if (!sources.length) return null;

  return (
    <Accordion type="single" collapsible className="mt-3 rounded-lg border border-slate-200 bg-white px-3">
      <AccordionItem value="sources" className="border-0">
        <AccordionTrigger>RAG 来源 ({sources.length})</AccordionTrigger>
        <AccordionContent>
          <div className="space-y-2">
            {sources.map((source, index) => (
              <div key={`${source.id || source.title}-${index}`} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <div className="font-medium text-slate-900">{source.title || "本地知识片段"}</div>
                <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                  {source.city && <span>{source.city}</span>}
                  {source.country && <span>{source.country}</span>}
                  {source.category && <span>{source.category}</span>}
                  {source.source && <span>{source.source}</span>}
                  {typeof source.score === "number" && <span>score {source.score.toFixed(2)}</span>}
                  {(source.source_url || source.url) && (
                    <a href={source.source_url || source.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                      打开来源
                    </a>
                  )}
                </div>
                {source.content && <p className="mt-2 line-clamp-3 text-xs leading-5 text-slate-600">{source.content}</p>}
              </div>
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
