import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'

const components: Components = {
  h1: ({ children }) => (
    <h1 className="font-display font-medium text-[length:var(--fs-display-sm)] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight mt-10 mb-4 max-w-[28ch]">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="font-display font-medium text-[28px] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight mt-8 mb-3 max-w-[32ch]">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="font-display font-medium text-[length:var(--fs-body-lg)] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight mt-6 mb-2 max-w-[36ch]">
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p className="font-sans text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)] mt-0 mb-5 max-w-[68ch]">
      {children}
    </p>
  ),
  ul: ({ children }) => (
    <ul className="font-sans text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-1)] mt-0 mb-5 max-w-[68ch] list-none pl-0 space-y-2">
      {children}
    </ul>
  ),
  li: ({ children }) => (
    <li className="pl-0 relative">
      <span className="font-serif text-[var(--chestnut)] mr-2">·</span>
      <span className="align-middle">{children}</span>
    </li>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-8 font-serif italic text-[length:var(--fs-quote)] leading-[1.4] text-[var(--chestnut)] max-w-[58ch]">
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <table className="w-full text-left border-collapse my-6">
      {children}
    </table>
  ),
  thead: ({ children }) => <thead>{children}</thead>,
  tbody: ({ children }) => <tbody>{children}</tbody>,
  tr: ({ children }) => (
    <tr className="border-b border-[var(--line)]">
      {children}
    </tr>
  ),
  th: ({ children }) => (
    <th className="py-2 pr-4 font-sans text-[length:var(--fs-body-sm)] font-semibold text-[var(--ink-1)] border-b border-[var(--line)]">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="py-2 pr-4 font-sans text-[length:var(--fs-body)] text-[var(--ink-2)]">
      {children}
    </td>
  ),
  code: ({ children }) => (
    <code className="font-mono text-[length:var(--fs-body-sm)] bg-[var(--bg-paper-2)] px-1.5 py-0.5 rounded text-[var(--ink-1)]">
      {children}
    </code>
  ),
  hr: () => <div className="my-10 border-t border-[var(--line)]" />,
}

export function EditorialMarkdown({ source }: { source: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {source}
    </ReactMarkdown>
  )
}
