import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { safeUrl } from "../research";
export default function Markdown({ value }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: ({ href, children }) => {
          const url = safeUrl(href);
          return url ? (
            <a href={url} target="_blank" rel="noreferrer">
              {children}
            </a>
          ) : (
            <span>{children}</span>
          );
        },
        img: ({ alt }) => <span>{alt || "[Image reference]"}</span>,
      }}
    >
      {value || ""}
    </ReactMarkdown>
  );
}
