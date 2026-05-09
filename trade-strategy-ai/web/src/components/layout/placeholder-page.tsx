import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from './page-header';

type PlaceholderPageProps = {
  title: string;
  description: string;
  note: string;
};

export function PlaceholderPage({ title, description, note }: PlaceholderPageProps) {
  return (
    <main className="page-stack">
      <PageHeader kicker="Stage 4 placeholder" title={title} description={description} />
      <Card>
        <CardHeader>
          <CardTitle>Coming next</CardTitle>
          <CardDescription>Shell complete, content will be connected in the next stage.</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-slate-300">
          <p>{note}</p>
        </CardContent>
      </Card>
    </main>
  );
}
