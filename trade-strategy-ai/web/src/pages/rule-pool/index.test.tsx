import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { RulePoolPage } from './index';
import { renderWithRouter } from '@/test/test-utils';

describe('RulePoolPage', () => {
  it('renders the rule pool placeholder page', async () => {
    renderWithRouter([{ path: '/rule-pool', element: <RulePoolPage /> }], ['/rule-pool']);

    expect(await screen.findByRole('heading', { name: '规则池' })).toBeInTheDocument();
    expect(screen.getByText(/正式信息架构/)).toBeInTheDocument();
  });
});
