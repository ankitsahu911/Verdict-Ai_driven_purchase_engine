import { type Transition, type Variants } from "framer-motion";

/**
 * Standard animation tokens for Verdict
 * Coherent design language across all 7 primary screens.
 */
export const DURATION_FAST = 0.18;
export const DURATION_NORMAL = 0.32;
export const DURATION_ENTER = 0.42;

export const EASE_OUT_CUBIC: [number, number, number, number] = [0.215, 0.61, 0.355, 1];
export const EASE_IN_OUT: [number, number, number, number] = [0.4, 0, 0.2, 1];

export const TRANSITION_NORMAL: Transition = {
  duration: DURATION_NORMAL,
  ease: EASE_OUT_CUBIC,
};

export const TRANSITION_ENTER: Transition = {
  duration: DURATION_ENTER,
  ease: EASE_OUT_CUBIC,
};

export const TRANSITION_FAST: Transition = {
  duration: DURATION_FAST,
  ease: "easeOut",
};

/**
 * Standard Motion Variants
 */
export const fadeUpVariants: Variants = {
  hidden: { opacity: 0, y: 14 },
  visible: {
    opacity: 1,
    y: 0,
    transition: TRANSITION_ENTER,
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: TRANSITION_FAST,
  },
};

export const fadeInVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: TRANSITION_NORMAL,
  },
  exit: {
    opacity: 0,
    transition: TRANSITION_FAST,
  },
};

export const scaleInVariants: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: TRANSITION_NORMAL,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: TRANSITION_FAST,
  },
};

export const staggerContainerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.04,
      delayChildren: 0.02,
    },
  },
};

export const staggerItemVariants: Variants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: TRANSITION_NORMAL,
  },
};

export const cardHoverMotion = {
  whileHover: { y: -2, transition: { duration: DURATION_FAST } },
  whileTap: { y: 0, transition: { duration: 0.1 } },
};
