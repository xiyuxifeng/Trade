import { EmptyState } from '@/components/kit';

type ProfileEmptyStateProps = {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function ProfileEmptyState({ title, description, actionLabel, onAction }: ProfileEmptyStateProps) {
  return <EmptyState title={title} description={description} actionLabel={actionLabel} onAction={onAction} />;
}
