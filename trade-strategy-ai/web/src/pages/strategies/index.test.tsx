import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { StrategiesPage } from './index';
import { renderWithRouter } from '@/test/test-utils';

describe('StrategiesPage', () => {
  it('renders the placeholder shell for the strategies center', () => {
    renderWithRouter([{ path: '/strategies', element: <StrategiesPage /> }], ['/strategies']);

    expect(screen.getByRole('heading', { name: 'Strategies' })).toBeInTheDocument();
    expect(screen.getByText('Stage 4 placeholder')).toBeInTheDocument();
    expect(screen.getByText('Coming next')).toBeInTheDocument();
    expect(screen.getByText('Strategy content will be connected in later stages.')).toBeInTheDocument();
  });
});
