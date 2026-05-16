import type { ReactNode } from 'react';

type ArtifactPreviewProps = {
  kind: string;
  content: string | null | undefined;
  title?: string;
};

type MarkdownBlock =
  | { type: 'heading'; level: 1 | 2 | 3 | 4 | 5 | 6; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'list'; items: string[] }
  | { type: 'quote'; text: string }
  | { type: 'code'; language: string; code: string };

function buildMarkdownBlocks(markdown: string): MarkdownBlock[] {
  // 用一个非常小的行级状态机解析 Markdown，避免引入 HTML 注入风险较高的第三方渲染器。
  const lines = markdown.replace(/\r\n/g, '\n').split('\n');
  const blocks: MarkdownBlock[] = [];
  let index = 0;

  while (index < lines.length) {
    const rawLine = lines[index];
    const line = rawLine.trimEnd();
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length as 1 | 2 | 3 | 4 | 5 | 6,
        text: headingMatch[2].trim(),
      });
      index += 1;
      continue;
    }

    if (trimmed.startsWith('```')) {
      const language = trimmed.slice(3).trim();
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith('```')) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) {
        index += 1;
      }
      blocks.push({ type: 'code', language, code: codeLines.join('\n') });
      continue;
    }

    if (/^[-*+]\s+/.test(trimmed)) {
      const items: string[] = [];
      while (index < lines.length) {
        const listLine = lines[index].trim();
        if (!/^[-*+]\s+/.test(listLine)) {
          break;
        }
        items.push(listLine.replace(/^[-*+]\s+/, '').trim());
        index += 1;
      }
      blocks.push({ type: 'list', items });
      continue;
    }

    if (trimmed.startsWith('>')) {
      const quoteLines: string[] = [];
      while (index < lines.length) {
        const quoteLine = lines[index].trim();
        if (!quoteLine.startsWith('>')) {
          break;
        }
        quoteLines.push(quoteLine.replace(/^>\s?/, '').trim());
        index += 1;
      }
      blocks.push({ type: 'quote', text: quoteLines.join(' ') });
      continue;
    }

    const paragraphLines: string[] = [trimmed];
    index += 1;
    while (index < lines.length) {
      const nextTrimmed = lines[index].trim();
      if (
        !nextTrimmed ||
        nextTrimmed.startsWith('>') ||
        nextTrimmed.startsWith('```') ||
        /^[-*+]\s+/.test(nextTrimmed) ||
        /^(#{1,6})\s+/.test(nextTrimmed)
      ) {
        break;
      }
      paragraphLines.push(nextTrimmed);
      index += 1;
    }
    blocks.push({ type: 'paragraph', text: paragraphLines.join(' ') });
  }

  return blocks;
}

function renderInlineText(text: string): ReactNode[] {
  const segments = text.split(/(`[^`]+`)/g);
  return segments.map((segment, index) => {
    if (segment.startsWith('`') && segment.endsWith('`') && segment.length > 1) {
      return (
        <code
          className="rounded bg-slate-900 px-1.5 py-0.5 font-mono text-[0.82em] text-sky-200"
          key={`${segment}-${index}`}
        >
          {segment.slice(1, -1)}
        </code>
      );
    }
    return <span key={`${segment}-${index}`}>{segment}</span>;
  });
}

function MarkdownPreview({ markdown }: { markdown: string }) {
  const blocks = buildMarkdownBlocks(markdown);

  return (
    <div className="space-y-4">
      {blocks.map((block, index) => {
        if (block.type === 'heading') {
          const HeadingTag = `h${block.level}` as 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
          return (
            <HeadingTag className="font-semibold text-slate-900" key={`heading-${index}`}>
              {renderInlineText(block.text)}
            </HeadingTag>
          );
        }

        if (block.type === 'list') {
          return (
            <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700" key={`list-${index}`}>
              {block.items.map((item, itemIndex) => (
                <li key={`${block.type}-${index}-${itemIndex}`}>{renderInlineText(item)}</li>
              ))}
            </ul>
          );
        }

        if (block.type === 'quote') {
          return (
            <blockquote
              className="border-l-4 border-sky-300 bg-sky-50 px-4 py-3 text-sm text-slate-700"
              key={`quote-${index}`}
            >
              {renderInlineText(block.text)}
            </blockquote>
          );
        }

        if (block.type === 'code') {
          return (
            <div className="space-y-2" key={`code-${index}`}>
              {block.language ? <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{block.language}</p> : null}
              <pre className="overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-800">
                <code className="whitespace-pre-wrap font-mono">{block.code}</code>
              </pre>
            </div>
          );
        }

        return (
          <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700" key={`paragraph-${index}`}>
            {renderInlineText(block.text)}
          </p>
        );
      })}
    </div>
  );
}

function HtmlPreviewFrame({ html, title = 'HTML 预览' }: { html: string; title?: string }) {
  return (
    <iframe
      aria-label={title}
      className="min-h-[30rem] w-full rounded-2xl border border-slate-800 bg-white"
      loading="lazy"
      sandbox="allow-same-origin"
      srcDoc={html}
      title={title}
    />
  );
}

function RawPreview({ content }: { content: string }) {
  return (
    <pre className="max-h-[36rem] overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-sm text-slate-200">
      {content}
    </pre>
  );
}

export function ArtifactPreview({ kind, content, title }: ArtifactPreviewProps) {
  const previewContent = content?.trim() ?? '';

  if (!previewContent) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
        暂无可用预览。
      </div>
    );
  }

  if (kind === 'html') {
    return <HtmlPreviewFrame html={previewContent} title={title ?? 'HTML 预览'} />;
  }

  if (kind === 'markdown') {
    return (
      <div className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Markdown preview</p>
          <p className="text-xs text-slate-500">已安全转义渲染</p>
        </div>
        <MarkdownPreview markdown={previewContent} />
      </div>
    );
  }

  return <RawPreview content={previewContent} />;
}
