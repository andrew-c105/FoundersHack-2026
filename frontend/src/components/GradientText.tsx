import type { ReactNode } from "react";
import "./GradientText.css";

export type GradientTextProps = {
  colors: string[];
  animationSpeed?: number;
  showBorder?: boolean;
  children: ReactNode;
  className?: string;
};

/**
 * Animated gradient text (react-bits GradientText-JS-CSS–style API).
 * Added manually; `npx shadcn@latest add` requires components.json + path aliases.
 */
export default function GradientText({
  colors,
  animationSpeed = 8,
  showBorder = false,
  children,
  className = "",
}: GradientTextProps) {
  const list = colors.length ? colors : ["#5227FF", "#FF9FFC", "#B19EEF"];
  const loop = [...list, list[0]];
  const bgImage = `linear-gradient(90deg, ${loop.join(", ")})`;

  return (
    <span
      className={`gradient-text ${className}`.trim()}
      style={{
        backgroundImage: bgImage,
        animationDuration: `${animationSpeed}s`,
        ...(showBorder
          ? { outline: "2px solid rgba(82, 39, 255, 0.35)", outlineOffset: "2px", borderRadius: "4px" }
          : {}),
      }}
    >
      {children}
    </span>
  );
}
