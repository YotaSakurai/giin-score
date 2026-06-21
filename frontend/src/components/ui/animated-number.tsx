"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface AnimatedNumberProps {
  value: number;
  decimals?: number;
  duration?: number;
  className?: string;
}

export function AnimatedNumber({ value, decimals = 0, duration = 800, className }: AnimatedNumberProps) {
  const [displayed, setDisplayed] = useState(0);
  const [animated, setAnimated] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  const startAnimation = useCallback(() => {
    const startTime = performance.now();
    const target = value;
    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      setDisplayed(eased * target);
      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setAnimated(true);
      }
    };
    requestAnimationFrame(animate);
  }, [value, duration]);

  useEffect(() => {
    if (animated) return;

    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          observer.disconnect();
          startAnimation();
        }
      },
      { threshold: 0.1 },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [animated, startAnimation]);

  // After animation completes, track value prop changes directly
  const finalValue = animated ? value : displayed;

  return (
    <span ref={ref} className={className}>
      {finalValue.toFixed(decimals)}
    </span>
  );
}
