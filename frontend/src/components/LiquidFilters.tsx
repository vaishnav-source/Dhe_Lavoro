export default function LiquidFilters() {
  return (
    <svg version="1.1" xmlns="http://www.w3.org/2000/svg" width="0" height="0">
      <defs>
        <filter id="liquid">
          <feGaussianBlur
            result="blur"
            stdDeviation={10}
            in="SourceGraphic"
          />
          <feColorMatrix
            result="liquid"
            values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 18 -7"
            mode="matrix"
            in="blur"
          />
        </filter>
      </defs>
    </svg>
  );
}