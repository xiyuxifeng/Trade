import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { ImportsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';

describe('ImportsPage', () => {
  it('renders the imports page title', async () => {
    renderWithRouter([{ path: '/imports', element: <ImportsPage /> }], ['/imports']);

    expect(await screen.findByText('Imports')).toBeInTheDocument();
  });
});
