import type { ProfileValidationStatus } from '@/types/profile';
import { StatusBadge } from '@/components/kit';

export function ProfileStatusBadge({ status }: { status: ProfileValidationStatus }) {
  return <StatusBadge value={status} />;
}
