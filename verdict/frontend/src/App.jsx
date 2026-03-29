import LandingInput from './components/LandingInput'
import CourtRoom from './components/CourtRoom'
import useVerdictStore from './store/verdictStore'

export default function App() {
  const screen = useVerdictStore((s) => s.screen)

  return (
    <div className="h-full w-full bg-void overflow-hidden">
      {screen === 'landing' ? (
        <div key="landing" className="h-full w-full">
          <LandingInput />
        </div>
      ) : (
        <div key="courtroom" className="h-full w-full courtroom-enter">
          <CourtRoom />
        </div>
      )}
    </div>
  )
}
