import { useParams } from 'react-router-dom';
import { AlertDetailPanel } from '@/features/alerts/alert-detail-panel';

export function AlertDetailPage() {
  const { recordId = '' } = useParams<{ recordId: string }>();
  return <AlertDetailPanel recordId={recordId} />;
}

