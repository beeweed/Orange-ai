// Compact tool activity blocks with expandable details.
// Each block shows a small toggle that reveals the LLM tool input schema
// summary, the actual arguments used for the call, and the tool output.
import { useMemo, useState } from 'react'
import { cn } from '../utils/cn'
import type { ToolActivity as ToolActivityType } from '../types'
import {
  CheckCircleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  CodeIcon,
  EyeIcon,
  RefreshIcon,
  SearchIcon,
  XCircleIcon,
} from './Icons'

interface Props {
  tool: ToolActivityType
  onOpenFile?: (path: string) => void
}

interface ToolDefinition {
  signature: string
  description: string
  fields: Array<{
    name: string
    type: string
    required?: boolean
    description: string
  }>
}

const FILE_TOOL_NAMES = new Set([
  'file_write',
  'file_read',
  'file_editor',
  'line_edit',
  'insert_after_line',
])

const TOOL_DEFINITIONS: Record<string, ToolDefinition> = {
  file_write: {
    signature: 'file_write(file_path: string, content: string)',
    description:
      'Create a new file or fully overwrite an existing file inside the sandbox.',
    fields: [
      {
        name: 'file_path',
        type: 'string',
        required: true,
        description: 'Absolute sandbox path, usually under /home/user/.',
      },
      {
        name: 'content',
        type: 'string',
        required: true,
        description: 'Full file contents to write.',
      },
    ],
  },
  file_read: {
    signature: 'file_read(file_path: string)',
    description: 'Read an existing sandbox file and return line-numbered content.',
    fields: [
      {
        name: 'file_path',
        type: 'string',
        required: true,
        description: 'Absolute sandbox path to the file being read.',
      },
    ],
  },
  file_editor: {
    signature:
      'file_editor(file_path: string, old_string: string, new_string: string, replace_all?: boolean)',
    description: 'Perform an exact string replacement in an existing sandbox file.',
    fields: [
      {
        name: 'file_path',
        type: 'string',
        required: true,
        description: 'Absolute sandbox path to the file being changed.',
      },
      {
        name: 'old_string',
        type: 'string',
        required: true,
        description: 'Exact text that must already exist in the file.',
      },
      {
        name: 'new_string',
        type: 'string',
        required: true,
        description: 'Replacement text for the matched content.',
      },
      {
        name: 'replace_all',
        type: 'boolean',
        description: 'Replace every match instead of only the first one.',
      },
    ],
  },
  line_edit: {
    signature:
      'line_edit(file_path: string, old_string_line_numbers: string, new_string: string)',
    description:
      'Replace one line or an inclusive range of lines in an existing sandbox file using file_read line numbers.',
    fields: [
      {
        name: 'file_path',
        type: 'string',
        required: true,
        description: 'Absolute sandbox path to the file being changed.',
      },
      {
        name: 'old_string_line_numbers',
        type: 'string',
        required: true,
        description: "Single line like '27' or inclusive range like '25-37' from file_read output.",
      },
      {
        name: 'new_string',
        type: 'string',
        required: true,
        description: 'Replacement content for the targeted line span.',
      },
    ],
  },
  insert_after_line: {
    signature: 'insert_after_line(file_path: string, line_number: number, content: string)',
    description: 'Insert a block of text immediately after a specific line.',
    fields: [
      {
        name: 'file_path',
        type: 'string',
        required: true,
        description: 'Absolute sandbox path to the file being modified.',
      },
      {
        name: 'line_number',
        type: 'number',
        required: true,
        description: 'The line number after which the content is inserted.',
      },
      {
        name: 'content',
        type: 'string',
        required: true,
        description: 'Text or code block to insert.',
      },
    ],
  },
  web_search: {
    signature: 'web_search(query: string)',
    description:
      'Search the live web with Tavily and return compact result objects containing title, url, and Description.',
    fields: [
      {
        name: 'query',
        type: 'string',
        required: true,
        description: 'Search query for recent, real-time, or otherwise unknown information.',
      },
    ],
  },
  fatch_web_urls: {
    signature: 'fatch_web_urls(url: string)',
    description:
      'Fetch one URL with Firecrawl and return clean page content for deeper reasoning.',
    fields: [
      {
        name: 'url',
        type: 'string',
        required: true,
        description: 'Single http(s) URL to fetch and extract.',
      },
    ],
  },
}

function stringifyPayload(value: Record<string, unknown> | undefined, fallback: string) {
  if (!value || Object.keys(value).length === 0) return fallback
  return JSON.stringify(value, null, 2)
}

function tryParseJson(value: string | undefined) {
  if (!value) return null
  try {
    return JSON.parse(value) as unknown
  } catch {
    return null
  }
}

export function ToolActivityChip({ tool, onOpenFile }: Props) {
  const [expanded, setExpanded] = useState(false)

  const isFileTool = FILE_TOOL_NAMES.has(tool.name)
  const isWrite = tool.name === 'file_write'
  const isEdit = tool.name === 'file_editor'
  const isLineEdit = tool.name === 'line_edit'
  const isInsert = tool.name === 'insert_after_line'
  const isSearch = tool.name === 'web_search'
  const isFetch = tool.name === 'fatch_web_urls'

  const verb = isWrite
    ? 'create'
    : isEdit
      ? 'edit'
      : isLineEdit
        ? 'line-edit'
        : isInsert
          ? 'insert'
          : isSearch
            ? 'search'
            : isFetch
              ? 'fetch'
              : tool.name === 'file_read'
                ? 'read'
                : tool.name

  const summaryValue = isFileTool
    ? tool.filePath ?? tool.display.replace(/^[^:]*:\s*/, '')
    : tool.display.replace(/^[^:]*:\s*/, '') || tool.name

  const statusColor =
    tool.status === 'success'
      ? 'border-emerald-500/25 bg-emerald-500/[0.06]'
      : tool.status === 'error'
        ? 'border-destructive/30 bg-destructive/[0.06]'
        : 'border-primary/25 bg-primary/[0.06]'

  const schema = TOOL_DEFINITIONS[tool.name]
  const inputText = useMemo(
    () => stringifyPayload(tool.arguments, 'No tool arguments were captured for this call.'),
    [tool.arguments],
  )
  const outputText =
    tool.result || (tool.status === 'running' ? 'Waiting for tool output…' : 'No output available.')

  const parsedResult = useMemo(() => tryParseJson(tool.result), [tool.result])
  const searchResults = Array.isArray(parsedResult) ? parsedResult : null
  const fetchedPage =
    parsedResult && typeof parsedResult === 'object' && !Array.isArray(parsedResult)
      ? (parsedResult as Record<string, unknown>)
      : null

  return (
    <div
      className={cn(
        'inline-flex max-w-full flex-col overflow-hidden rounded-xl border transition-all duration-200',
        statusColor,
      )}
    >
      <div className="flex max-w-full items-center gap-2 px-2.5 py-1.5">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-white/5">
          {isFileTool ? (
            <CodeIcon className="h-3 w-3 text-blue-400" />
          ) : isSearch ? (
            <SearchIcon className="h-3 w-3 text-sky-400" />
          ) : (
            <EyeIcon className="h-3 w-3 text-accent" />
          )}
        </span>

        <span className="shrink-0 font-mono text-[11px] text-muted-foreground">{verb}:</span>

        {isFileTool && summaryValue && onOpenFile ? (
          <button
            type="button"
            onClick={() => onOpenFile(summaryValue)}
            className="max-w-[220px] truncate font-mono text-[11px] text-foreground/90 transition-colors hover:text-foreground"
            title={`Open ${summaryValue}`}
          >
            {summaryValue}
          </button>
        ) : (
          <span className="max-w-[220px] truncate font-mono text-[11px] text-foreground/90">
            {summaryValue || tool.name}
          </span>
        )}

        <span className="ml-auto flex shrink-0 items-center gap-1.5">
          {tool.status === 'running' && (
            <RefreshIcon className="h-3.5 w-3.5 animate-spin text-primary" />
          )}
          {tool.status === 'success' && (
            <CheckCircleIcon className="h-3.5 w-3.5 text-emerald-500" />
          )}
          {tool.status === 'error' && (
            <XCircleIcon className="h-3.5 w-3.5 text-destructive" />
          )}
          <button
            type="button"
            onClick={() => setExpanded((current) => !current)}
            aria-expanded={expanded}
            aria-label={expanded ? 'Hide tool details' : 'Show tool details'}
            className="inline-flex h-5 w-5 items-center justify-center rounded-md border border-white/8 bg-white/[0.04] text-muted-foreground transition-all hover:text-foreground hover:bg-white/[0.08]"
            title={expanded ? 'Hide input/output' : 'Show input/output'}
          >
            {expanded ? (
              <ChevronDownIcon className="h-3 w-3" />
            ) : (
              <ChevronRightIcon className="h-3 w-3" />
            )}
          </button>
        </span>
      </div>

      {expanded && (
        <div className="border-t border-white/8 bg-black/20 px-2.5 py-2">
          <div className="grid gap-2 lg:grid-cols-2">
            <section className="min-w-0 rounded-lg border border-white/8 bg-white/[0.03] p-2">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Input
                </span>
                <span className="rounded-full border border-white/8 px-1.5 py-0.5 text-[9px] font-medium text-muted-foreground">
                  LLM schema
                </span>
              </div>

              {schema ? (
                <div className="mb-2 space-y-1.5 text-[11px] text-muted-foreground">
                  <p className="font-mono text-[10px] text-foreground/85">{schema.signature}</p>
                  <p>{schema.description}</p>
                  <div className="space-y-1">
                    {schema.fields.map((field) => (
                      <div key={field.name} className="rounded-md bg-black/20 px-2 py-1">
                        <div className="flex items-center gap-1.5 text-[10px] text-foreground/85">
                          <span className="font-mono">{field.name}</span>
                          <span className="text-muted-foreground">{field.type}</span>
                          {field.required && (
                            <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[9px] text-primary">
                              required
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 text-[10px] leading-relaxed text-muted-foreground">
                          {field.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="mb-2 text-[11px] text-muted-foreground">
                  No predefined schema summary is available for this tool.
                </p>
              )}

              <div className="rounded-md bg-[#0f1115] p-2">
                <div className="mb-1 text-[10px] font-medium text-muted-foreground">Arguments</div>
                <pre className="max-h-44 overflow-auto whitespace-pre-wrap break-all font-mono text-[10px] leading-relaxed text-foreground/88">
                  {inputText}
                </pre>
              </div>
            </section>

            <section className="min-w-0 rounded-lg border border-white/8 bg-white/[0.03] p-2">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Output
                </span>
                <span className="rounded-full border border-white/8 px-1.5 py-0.5 text-[9px] font-medium text-muted-foreground">
                  Tool result
                </span>
              </div>

              {isSearch && searchResults ? (
                <div className="space-y-2">
                  <div className="rounded-md bg-[#0f1115] px-2 py-1.5 text-[10px] text-muted-foreground">
                    {searchResults.length} search result{searchResults.length === 1 ? '' : 's'}
                  </div>
                  <div className="max-h-72 space-y-2 overflow-auto rounded-md bg-[#0f1115] p-2">
                    {searchResults.map((entry, index) => {
                      const item = entry as Record<string, unknown>
                      return (
                        <div key={`${String(item.url)}-${index}`} className="rounded-md border border-white/8 bg-white/[0.03] p-2">
                          <div className="text-[11px] font-semibold text-foreground/92">
                            {String(item.title ?? 'Untitled result')}
                          </div>
                          <div className="mt-1 break-all font-mono text-[10px] text-sky-300/90">
                            {String(item.url ?? '')}
                          </div>
                          <p className="mt-1 whitespace-pre-wrap text-[10px] leading-relaxed text-muted-foreground">
                            {String(item.Description ?? '')}
                          </p>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ) : isFetch && fetchedPage ? (
                <div className="space-y-2">
                  <div className="rounded-md bg-[#0f1115] px-2 py-1.5 font-mono text-[10px] text-sky-300/90 break-all">
                    {String(fetchedPage.url ?? tool.meta?.url ?? 'Unknown URL')}
                  </div>
                  <div className="rounded-md bg-[#0f1115] p-2">
                    <div className="mb-1 text-[10px] font-medium text-muted-foreground">Fetched content</div>
                    <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words font-mono text-[10px] leading-relaxed text-foreground/88">
                      {String(fetchedPage.content ?? '')}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="rounded-md bg-[#0f1115] p-2">
                  <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words font-mono text-[10px] leading-relaxed text-foreground/88">
                    {outputText}
                  </pre>
                </div>
              )}
            </section>
          </div>
        </div>
      )}
    </div>
  )
}