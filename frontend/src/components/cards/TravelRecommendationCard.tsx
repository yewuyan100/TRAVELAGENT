interface TravelRecommendationCardProps {
  city: string;
  title: string;
  description: string;
  tags?: string[];
}

export function TravelRecommendationCard({ city, title, description, tags = [] }: TravelRecommendationCardProps) {
  return (
    <div className="mt-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{city}</div>
      <h3 className="mt-1 text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
      {!!tags.length && (
        <div className="mt-3 flex flex-wrap gap-2">
          {tags.map((tag) => (
            <span key={tag} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">{tag}</span>
          ))}
        </div>
      )}
    </div>
  );
}
