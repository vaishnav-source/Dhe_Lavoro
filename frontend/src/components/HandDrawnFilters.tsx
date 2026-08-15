export default function HandDrawnFilters() {
  return (
    <svg height={0} width={0} style={{ position: "absolute" }}>
      <filter id="handDrawnNoise">
        <feTurbulence
          result="noise"
          numOctaves={8}
          baseFrequency="0.1"
          type="fractalNoise"
        />
        <feDisplacementMap
          yChannelSelector="G"
          xChannelSelector="R"
          scale={3}
          in2="noise"
          in="SourceGraphic"
        />
      </filter>
      <filter id="handDrawnNoise2">
        <feTurbulence
          result="noise"
          numOctaves={8}
          baseFrequency="0.1"
          seed={1010}
          type="fractalNoise"
        />
        <feDisplacementMap
          yChannelSelector="G"
          xChannelSelector="R"
          scale={3}
          in2="noise"
          in="SourceGraphic"
        />
      </filter>
      <filter id="handDrawnNoiset">
        <feTurbulence
          result="noise"
          numOctaves={8}
          baseFrequency="0.1"
          type="fractalNoise"
        />
        <feDisplacementMap
          yChannelSelector="G"
          xChannelSelector="R"
          scale={6}
          in2="noise"
          in="SourceGraphic"
        />
      </filter>
      <filter id="handDrawnNoiset2">
        <feTurbulence
          result="noise"
          numOctaves={8}
          baseFrequency="0.1"
          seed={1010}
          type="fractalNoise"
        />
        <feDisplacementMap
          yChannelSelector="G"
          xChannelSelector="R"
          scale={6}
          in2="noise"
          in="SourceGraphic"
        />
      </filter>
    </svg>
  );
}