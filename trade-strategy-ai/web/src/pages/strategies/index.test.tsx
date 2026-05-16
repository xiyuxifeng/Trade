import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { StrategiesPage } from './index';
import { renderWithRouter } from '@/test/test-utils';

describe('StrategiesPage', () => {
  it('renders the formal strategies entry page', () => {
    renderWithRouter([{ path: '/strategies', element: <StrategiesPage /> }], ['/strategies']);

    expect(screen.getByRole('heading', { name: '策略' })).toBeInTheDocument();
    expect(screen.getByText('V2 正式入口')).toBeInTheDocument();
    expect(screen.getByText('策略工作台正在收口到正式界面')).toBeInTheDocument();
  });
});
