export const landingFade = {
  initial: { opacity: 0, y: 28 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.25 },
  transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] as const },
};

export const landingLift = {
  whileHover: { y: -4 },
  transition: { duration: 0.2 },
};
