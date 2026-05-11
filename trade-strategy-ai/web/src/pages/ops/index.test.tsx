import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { OpsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';

describe('OpsPage', () => {
  it('renders the placeholder shell for the operations center', () => {
    renderWithRouter([{ path: '/ops', element: <OpsPage /> }], ['/ops']);

    expect(screen.getByRole('heading', { name: 'Ops' })).toBeInTheDocument();
    expect(screen.getByText('Stage 4 placeholder')).toBeInTheDocument();
    expect(screen.getByText('Coming next')).toBeInTheDocument();
    expect(screen.getByText('Operational tooling will land with deployment and recovery stages.')).toBeInTheDocument();
  });
});
