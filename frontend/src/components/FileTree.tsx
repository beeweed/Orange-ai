// File explorer tree. Converts the backend's flat path list into a nested tree
// and renders an interactive, collapsible structure (VS Code style).
import { useMemo, useState } from 'react'
import type { FileNode } from '../types'
import { cn } from '../utils/cn'
import {
  ChevronDownIcon,
  ChevronRightIcon,
  CodeIcon,
  FileIcon,
  FolderIcon,
} from './Icons'

interface TreeNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children: TreeNode[]
}

const ROOT = '/home/user'

function buildTree(files: FileNode[]): TreeNode[] {
  const root: TreeNode = { name: ROOT, path: ROOT, type: 'directory', children: [] }
  const dirMap = new Map<string, TreeNode>([[ROOT, root]])

  // Ensure directory nodes exist for every path segment.
  const ensureDir = (dirPath: string): TreeNode => {
    if (dirMap.has(dirPath)) return dirMap.get(dirPath)!
    const parentPath = dirPath.slice(0, dirPath.lastIndexOf('/')) || ROOT
    const parent = ensureDir(parentPath)
    const node: TreeNode = {
      name: dirPath.slice(dirPath.lastIndexOf('/') + 1),
      path: dirPath,
      type: 'directory',
      children: [],
    }
    parent.children.push(node)
    dirMap.set(dirPath, node)
    return node
  }

  for (const f of files) {
    if (!f.path.startsWith(ROOT)) continue
    const parentPath = f.path.slice(0, f.path.lastIndexOf('/')) || ROOT
    const parent = ensureDir(parentPath)
    if (f.type === 'directory') {
      ensureDir(f.path)
    } else {
      parent.children.push({
        name: f.path.slice(f.path.lastIndexOf('/') + 1),
        path: f.path,
        type: 'file',
        children: [],
      })
    }
  }

  const sortRec = (node: TreeNode) => {
    node.children.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'directory' ? -1 : 1
      return a.name.localeCompare(b.name)
    })
    node.children.forEach(sortRec)
  }
  sortRec(root)
  return root.children
}

function fileColor(name: string): string {
  if (/\.(css|scss)$/.test(name)) return 'text-purple-400'
  if (/\.(json)$/.test(name)) return 'text-green-400'
  if (/\.(ts|tsx|js|jsx|py)$/.test(name)) return 'text-blue-400'
  return 'text-muted-foreground'
}

function Node({
  node,
  depth,
  selected,
  onSelect,
}: {
  node: TreeNode
  depth: number
  selected: string | null
  onSelect: (path: string) => void
}) {
  const [open, setOpen] = useState(depth < 2)

  if (node.type === 'directory') {
    return (
      <div>
        <div
          className="flex items-center gap-1.5 px-2 py-1.5 cursor-pointer hover:bg-white/5 transition-all duration-150"
          style={{ paddingLeft: 8 + depth * 14 }}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? (
            <ChevronDownIcon className="w-3 h-3 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRightIcon className="w-3 h-3 text-muted-foreground shrink-0" />
          )}
          <FolderIcon className="w-4 h-4 text-yellow-500 shrink-0" />
          <span className="text-[13px] text-foreground truncate">{node.name}</span>
        </div>
        {open &&
          node.children.map((c) => (
            <Node
              key={c.path}
              node={c}
              depth={depth + 1}
              selected={selected}
              onSelect={onSelect}
            />
          ))}
      </div>
    )
  }

  const isSelected = selected === node.path
  const isCode = /\.(ts|tsx|js|jsx|py)$/.test(node.name)

  return (
    <div
      className={cn(
        'flex items-center gap-1.5 px-2 py-1.5 cursor-pointer rounded-lg transition-all duration-150 mx-1',
        isSelected ? 'bg-primary/15 text-primary hover:bg-primary/20' : 'hover:bg-white/5',
      )}
      style={{ paddingLeft: 8 + depth * 14 }}
      onClick={() => onSelect(node.path)}
    >
      {isCode ? (
        <CodeIcon className={cn('w-4 h-4 shrink-0', fileColor(node.name))} />
      ) : (
        <FileIcon className={cn('w-4 h-4 shrink-0', fileColor(node.name))} />
      )}
      <span className="text-[13px] truncate">{node.name}</span>
    </div>
  )
}

interface Props {
  files: FileNode[]
  selected: string | null
  onSelect: (path: string) => void
}

export function FileTree({ files, selected, onSelect }: Props) {
  const tree = useMemo(() => buildTree(files), [files])

  if (tree.length === 0) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="text-xs text-muted-foreground">No files yet.</p>
        <p className="text-[11px] text-muted-foreground/70 mt-1">
          Files created by the agent appear here.
        </p>
      </div>
    )
  }

  return (
    <div className="py-2">
      {tree.map((n) => (
        <Node key={n.path} node={n} depth={0} selected={selected} onSelect={onSelect} />
      ))}
    </div>
  )
}
