export default function VerdictLogo() {
  return (
    <div className="flex items-center gap-3">
      <div className="w-8 h-8 rounded-lg bg-gold/10 flex items-center justify-center">
        <span className="text-gold text-lg">⚖</span>
      </div>
      <h1 className="text-xl font-semibold tracking-tight text-[var(--text-primary)]">Verdict</h1>
    </div>
  )
}
