import React, { useState, useMemo } from 'react';
import DOMPurify from 'dompurify';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Eye, 
  Code, 
  Copy, 
  Check, 
  DownloadSimple, 
  X, 
  FileHtml, 
  FileText,
  Sparkle
} from '@phosphor-icons/react';

export default function ArtifactViewer({
  artifact,
  isOpen,
  onClose,
}) {
  const [activeTab, setActiveTab] = useState('preview'); // 'preview' | 'code'
  const [copied, setCopied] = useState(false);

  // Sanitize HTML defensively with DOMPurify and inject clean CSS reset
  const sanitizedHtml = useMemo(() => {
    if (!artifact || artifact.type !== 'html') return '';
    const cleanBody = DOMPurify.sanitize(artifact.content, {
      ADD_TAGS: ['style', 'script', 'button', 'input', 'select', 'textarea'],
      ADD_ATTR: ['onclick', 'onchange', 'style', 'class', 'id', 'type', 'value', 'placeholder'],
    });

    return `
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
          <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { 
              font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
              background: #ffffff; 
              color: #09090b; 
              padding: 1.5rem; 
              line-height: 1.5;
            }
          </style>
        </head>
        <body>
          ${cleanBody}
        </body>
      </html>
    `;
  }, [artifact]);

  if (!isOpen || !artifact) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(artifact.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const handleDownload = () => {
    const extension = artifact.type === 'html' ? 'html' : 'md';
    const filename = `${(artifact.title || 'artifact').toLowerCase().replace(/[^a-z0-9]+/g, '-')}.${extension}`;
    const blob = new Blob([artifact.content], { type: artifact.type === 'html' ? 'text/html' : 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const isHtml = artifact.type === 'html';

  return (
    <div className="flex-1 lg:w-1/2 h-full bg-zinc-950 border-l border-zinc-800 flex flex-col z-20 shadow-2xl transition-all">
      {/* Top Header Bar */}
      <div className="h-12 border-b border-zinc-800 px-4 flex items-center justify-between bg-zinc-900/70">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-5 h-5 rounded bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 flex-shrink-0">
            {isHtml ? <FileHtml size={12} weight="bold" /> : <FileText size={12} weight="bold" />}
          </div>
          <div className="min-w-0">
            <h3 className="text-xs font-semibold text-zinc-100 truncate">
              {artifact.title || 'Generated Asset'}
            </h3>
          </div>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 border border-zinc-700 text-amber-400 uppercase">
            {artifact.type}
          </span>
        </div>

        {/* View Switcher & Action Buttons */}
        <div className="flex items-center gap-1.5">
          {/* Tab Switcher */}
          <div className="flex items-center bg-zinc-950 border border-zinc-800 rounded-md p-0.5 mr-2">
            <button
              onClick={() => setActiveTab('preview')}
              className={`flex items-center gap-1 px-2.5 py-0.5 text-xs rounded transition-colors ${
                activeTab === 'preview'
                  ? 'bg-zinc-800 text-zinc-100 font-medium'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Eye size={12} />
              <span>Preview</span>
            </button>
            <button
              onClick={() => setActiveTab('code')}
              className={`flex items-center gap-1 px-2.5 py-0.5 text-xs rounded transition-colors ${
                activeTab === 'code'
                  ? 'bg-zinc-800 text-zinc-100 font-medium'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Code size={12} />
              <span>Raw</span>
            </button>
          </div>

          {/* Copy Button */}
          <button
            onClick={handleCopy}
            title="Copy Raw Content"
            className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
          </button>

          {/* Download Button */}
          <button
            onClick={handleDownload}
            title={`Download as .${isHtml ? 'html' : 'md'}`}
            className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <DownloadSimple size={14} />
          </button>

          {/* Close Button */}
          <button
            onClick={onClose}
            title="Close Canvas"
            className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-rose-400 transition-colors ml-1"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Main Canvas Body */}
      <div className="flex-1 overflow-hidden relative bg-zinc-950">
        {activeTab === 'preview' ? (
          isHtml ? (
            /* Sandboxed iframe for safe HTML rendering */
            <div className="w-full h-full p-3 bg-zinc-900/30">
              <iframe
                title="Artifact Sandbox"
                sandbox="allow-scripts"
                srcDoc={sanitizedHtml}
                className="w-full h-full border border-zinc-800 rounded-lg shadow-inner bg-white"
              />
            </div>
          ) : (
            /* Markdown rendering */
            <div className="w-full h-full overflow-y-auto p-6 text-zinc-200 bg-zinc-950">
              <div className="max-w-2xl mx-auto prose-custom">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {artifact.content}
                </ReactMarkdown>
              </div>
            </div>
          )
        ) : (
          /* Raw Code View */
          <div className="w-full h-full overflow-y-auto p-4 bg-zinc-950 font-mono text-xs text-zinc-300">
            <pre className="p-4 rounded-lg bg-zinc-900/70 border border-zinc-800 overflow-x-auto whitespace-pre-wrap leading-relaxed">
              <code>{artifact.content}</code>
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
