export const FADE_MS = 200;

export const fadeUp = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: FADE_MS / 1000, ease: "easeOut" as const },
};

export const chartFade = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  transition: { duration: FADE_MS / 1000 },
};

export const cardHover = {
  whileHover: { y: -2 },
  transition: { duration: 0.18 },
};
