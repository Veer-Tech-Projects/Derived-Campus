type CropSquareIconProps = {
  className?: string;
};

export function CropSquareIcon({ className }: CropSquareIconProps) {
  return (
    <svg
      viewBox="0 0 256 256"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M32 48H112C120.837 48 128 55.1634 128 64V192C128 200.837 135.163 208 144 208H224"
        stroke="currentColor"
        strokeWidth="18"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M208 32V112C208 120.837 200.837 128 192 128H64C55.1634 128 48 135.163 48 144V224"
        stroke="currentColor"
        strokeWidth="18"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}