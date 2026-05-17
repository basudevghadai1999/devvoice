export default function VoiceOrb({ state }) {
  return (
    <div className={`orb-scene state-${state}`}>
      {/* Ambient background glow */}
      <div className="ambient" />

      {/* Expanding rings */}
      <div className="ring r4" />
      <div className="ring r3" />
      <div className="ring r2" />
      <div className="ring r1" />

      {/* Core orb */}
      <div className="orb">
        <div className="orb-halo" />
        <div className="orb-surface" />
        <div className="orb-shine" />
      </div>
    </div>
  )
}
