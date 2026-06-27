// Minimal, safe Markdown -> HTML renderer for assistant messages.
// Escapes HTML first to prevent XSS, then applies a small subset of Markdown:
// fenced code blocks, inline code, bold, italics, headings, lists, links.

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

export function renderMarkdown(input: string): string {
  if (!input) return ''

  const codeBlocks: string[] = []
  // Extract fenced code blocks first so their contents aren't transformed.
  let text = input.replace(/```(\w+)?\n?([\s\S]*?)```/g, (_m, _lang, code) => {
    const idx = codeBlocks.length
    codeBlocks.push(
      `<pre><code>${escapeHtml(String(code).replace(/\n$/, ''))}</code></pre>`,
    )
    return `\u0000CODEBLOCK${idx}\u0000`
  })

  text = escapeHtml(text)

  // Inline code
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>')
  // Bold
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  // Italics
  text = text.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>')
  // Headings
  text = text.replace(/^###\s+(.*)$/gm, '<h3>$1</h3>')
  text = text.replace(/^##\s+(.*)$/gm, '<h2>$1</h2>')
  text = text.replace(/^#\s+(.*)$/gm, '<h1>$1</h1>')
  // Links
  text = text.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-primary underline">$1</a>',
  )

  // Unordered lists
  text = text.replace(/(?:^|\n)((?:[-*]\s+.*(?:\n|$))+)/g, (block) => {
    const items = block
      .trim()
      .split('\n')
      .map((l) => l.replace(/^[-*]\s+/, ''))
      .map((l) => `<li>${l}</li>`)
      .join('')
    return `\n<ul>${items}</ul>`
  })

  // Paragraphs / line breaks
  text = text
    .split(/\n{2,}/)
    .map((chunk) => {
      const t = chunk.trim()
      if (!t) return ''
      if (/^<(h\d|ul|ol|pre|blockquote)/.test(t)) return t
      if (t.includes('\u0000CODEBLOCK')) return t
      return `<p>${t.replace(/\n/g, '<br/>')}</p>`
    })
    .join('\n')

  // Restore code blocks
  text = text.replace(/\u0000CODEBLOCK(\d+)\u0000/g, (_m, i) => codeBlocks[Number(i)] || '')

  return text
}
