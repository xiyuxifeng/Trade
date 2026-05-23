import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Select } from '@/components/ui/select';
import { listTraderOptions } from '@/lib/api/traders';
import type { TraderOptionsSource } from '@/types/traders';

type TraderIdSelectProps = {
  source: TraderOptionsSource;
  value: string;
  onChange: (value: string) => void;
  ariaLabel: string;
  className?: string;
  disabled?: boolean;
};

export function TraderIdSelect({ source, value, onChange, ariaLabel, className, disabled = false }: TraderIdSelectProps) {
  const traderOptionsQuery = useQuery({
    queryKey: ['trader-options', source],
    queryFn: () => listTraderOptions({ source }),
    staleTime: 60_000,
  });

  const traderOptions = traderOptionsQuery.data?.items ?? [];

  useEffect(() => {
    if (!traderOptions.length) {
      return;
    }
    if (!value || !traderOptions.includes(value)) {
      onChange(traderOptions[0]);
    }
  }, [onChange, traderOptions, value]);

  const selectDisabled = disabled || traderOptionsQuery.isLoading || traderOptions.length === 0;
  const placeholder = traderOptionsQuery.isError
    ? '交易员选项加载失败'
    : traderOptionsQuery.isLoading
      ? '正在加载交易员选项'
      : '暂无可用交易员';

  return (
    <Select
      aria-label={ariaLabel}
      className={className}
      disabled={selectDisabled}
      onChange={(event) => onChange(event.target.value)}
      value={value}
    >
      {traderOptions.length === 0 ? <option value="">{placeholder}</option> : null}
      {traderOptions.map((traderId) => (
        <option key={traderId} value={traderId}>
          {traderId}
        </option>
      ))}
    </Select>
  );
}
