import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ArtifactPreview } from './artifact-preview';

describe('ArtifactPreview', () => {
  it('renders html in a sandboxed iframe', () => {
    render(<ArtifactPreview content="<html><body><h1>Report</h1></body></html>" kind="html" />);

    const frame = screen.getByTitle('HTML 预览');
    expect(frame).toHaveAttribute('sandbox', 'allow-same-origin');
    expect(frame).toHaveAttribute('srcdoc', '<html><body><h1>Report</h1></body></html>');
  });

  it('renders markdown without treating raw html as executable content', () => {
    render(
      <ArtifactPreview
        content={`# Title\n\n- First item\n- Second item\n\n\`\`\`ts\nconst value = 1;\n\`\`\`\n\n<script>alert(1)</script>`}
        kind="markdown"
      />,
    );

    expect(screen.getByRole('heading', { name: 'Title' })).toBeInTheDocument();
    expect(screen.getByText('First item')).toBeInTheDocument();
    expect(screen.getByText('Second item')).toBeInTheDocument();
    expect(screen.getByText('ts')).toBeInTheDocument();
    expect(screen.getByText('const value = 1;')).toBeInTheDocument();
    expect(screen.getByText('<script>alert(1)</script>')).toBeInTheDocument();
    expect(document.querySelector('script')).toBeNull();
  });
});

