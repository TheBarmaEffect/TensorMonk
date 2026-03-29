export default function VerdictLogo({ size = 'large' }) {
  const isLarge = size === 'large'
  const svgSize = isLarge ? 56 : 28
  const textSize = isLarge ? 'text-lg tracking-[0.35em]' : 'text-[11px] tracking-[0.25em]'

  return (
    <div className={`flex flex-col items-center ${isLarge ? 'gap-5' : 'gap-1.5'}`}>
      <svg
        width={svgSize}
        height={svgSize}
        viewBox="0 0 64 64"
        fill="none"
        className="logo-draw-in"
      >
        <line x1="12" y1="12" x2="32" y2="52" stroke="white" strokeWidth="2.5" strokeLinecap="round" className="logo-line logo-line-1" pathLength="1" />
        <line x1="52" y1="12" x2="32" y2="52" stroke="white" strokeWidth="2.5" strokeLinecap="round" className="logo-line logo-line-2" pathLength="1" />
        <line x1="36" y1="28" x2="50" y2="22" stroke="white" strokeWidth="2" strokeLinecap="round" className="logo-line logo-line-3" pathLength="1" />
        <circle cx="32" cy="52" r="2.5" fill="#f59e0b" className="logo-dot" />
      </svg>

      <h1 className={`font-display font-semibold ${textSize} text-white/90 uppercase`}>
        Verdict
      </h1>

      {isLarge && (
        <p className="font-body text-[13px] text-white/25 font-light tracking-wide">
          Every decision deserves a challenger.
        </p>
      )}
    </div>
  )
}
