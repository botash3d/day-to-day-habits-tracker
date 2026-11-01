import { Children, isValidElement, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import CodeBox from "./CodeBox";

// Plain text of a React tree, so the Copy button ignores the highlight spans.
function textOf(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (isValidElement(node)) {
    return textOf((node.props as { children?: ReactNode }).children);
  }
  return "";
}

function languageOf(children: ReactNode): string {
  const first = Children.toArray(children)[0];
  if (isValidElement(first)) {
    const className = (first.props as { className?: string }).className ?? "";
    const match = /language-([\w-]+)/.exec(className);
    if (match) return match[1];
  }
  return "";
}

const components: Components = {
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  pre: ({ children }) => (
    <CodeBox
      label={languageOf(children) || "code"}
      text={textOf(children).replace(/\n$/, "")}
    >
      {children}
    </CodeBox>
  ),
};

export default function LessonMarkdown({ children }: { children: string }) {
  return (
    <div className="learn-prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={components}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}