export default function AmberAlert({ donorName, replyText, requestId, onPromote }) {
  return (
    <div className="rounded-lg border border-amber/40 bg-amber/10 px-4 py-3 flex items-start gap-3">
      <span className="material-symbols-outlined text-amber text-[20px] animate-pulse-slow mt-0.5">
        warning
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-amber leading-tight">
          Soft-cancel risk detected
        </p>
        <p className="text-xs text-on-surface-variant mt-1 truncate">
          <span className="font-medium">{donorName}</span> replied:{' '}
          <span className="italic">"{replyText}"</span>
        </p>
      </div>
      {onPromote && (
        <button
          onClick={onPromote}
          className="shrink-0 text-xs font-semibold px-3 py-1.5 rounded bg-amber text-white hover:bg-amber/90 transition-colors"
        >
          Promote Standby
        </button>
      )}
    </div>
  )
}
