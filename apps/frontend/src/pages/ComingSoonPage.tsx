interface ComingSoonPageProps {
  title: string;
  description: string;
}

/** Placeholder route. Full pages are later phases. */
export default function ComingSoonPage({ title, description }: ComingSoonPageProps) {
  return (
    <section className="mx-auto max-w-xl rounded-xl border border-border bg-surface p-8">
      <p className="text-xs font-medium uppercase tracking-wide text-ai">Later phase</p>
      <h1 className="mt-2 text-2xl font-semibold">{title}</h1>
      <p className="mt-3 text-sm text-muted">{description}</p>
    </section>
  );
}
