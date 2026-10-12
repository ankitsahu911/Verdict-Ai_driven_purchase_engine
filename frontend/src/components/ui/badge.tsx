import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80",
        outline: "text-foreground",
        buy: "border-amber-600/30 bg-amber-600/15 text-amber-800 dark:text-amber-200 font-bold hover:bg-amber-600/25",
        consider:
          "border-stone-400/40 bg-stone-300/20 text-stone-800 dark:text-stone-200 font-bold hover:bg-stone-300/30",
        skip: "border-rose-500/30 bg-rose-500/15 text-rose-700 dark:text-rose-300 font-bold hover:bg-rose-500/25",
        neutral:
          "border-border bg-muted text-muted-foreground font-semibold",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
