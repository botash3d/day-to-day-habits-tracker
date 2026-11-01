import { useEffect, useRef, useState, type ReactNode } from "react";

function CopyButton({ text }: { text: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      // Clipboard access needs https or localhost.
      setState("failed");
    }
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setState("idle"), 1800);
  }

  return (
    <button type="button" className="icon-btn learn-copy" onClick={copy}>
      {state === "copied" ? "Copied" : state === "failed" ? "Copy failed" : "Copy"}
    </button>
  );
}

type Props = {
  label: string;
  // Plain text that the Copy button puts on the clipboard.
  text: string;
  children: ReactNode;
};

export default function CodeBox({ label, text, children }: Props) {
  return (
    <div className="learn-code">
      <div className="learn-code-bar">
        <span>{label}</span>
        <CopyButton text={text} />
      </div>
      <pre>{children}</pre>
    </div>
  );
}