import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2.5 whitespace-nowrap rounded-xl text-sm sm:text-base font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98] cursor-pointer [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-neutral-900 text-white shadow-md hover:bg-black hover:shadow-lg dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100",
        destructive:
          "bg-destructive text-destructive-foreground shadow hover:bg-destructive/90",
        outline:
          "border-2 border-neutral-300 dark:border-neutral-700 bg-white/90 dark:bg-neutral-900/90 text-foreground shadow-xs hover:border-neutral-900 dark:hover:border-white hover:bg-neutral-100/60 dark:hover:bg-neutral-800/60",
        secondary:
          "bg-secondary text-secondary-foreground border border-border/80 shadow-xs hover:bg-secondary/80",
        ghost: "hover:bg-neutral-100 dark:hover:bg-neutral-800 text-foreground",
        link: "text-foreground underline-offset-4 hover:underline",
      },
      size: {
        default: "h-11 px-6 py-2.5 text-sm sm:text-base tracking-wide",
        sm: "h-9.5 px-4 py-2 text-xs sm:text-sm font-semibold rounded-lg tracking-wide",
        lg: "h-13 px-8 py-3.5 text-base sm:text-lg font-bold tracking-wide rounded-2xl shadow-md",
        icon: "h-11 w-11 rounded-xl",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };