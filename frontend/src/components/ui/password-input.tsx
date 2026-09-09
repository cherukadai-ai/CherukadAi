import { Eye, EyeOff } from "lucide-react";
import { useState, type ComponentProps } from "react";

import { Input } from "@/components/ui/input";

interface PasswordInputProps extends Omit<ComponentProps<typeof Input>, "type"> {
  showLabel?: string;
  hideLabel?: string;
}

export function PasswordInput({
  className,
  showLabel = "Show password",
  hideLabel = "Hide password",
  ...props
}: PasswordInputProps) {
  const [isVisible, setIsVisible] = useState(false);
  const label = isVisible ? hideLabel : showLabel;

  return (
    <div className="relative">
      <Input
        {...props}
        className={`pr-10 ${className ?? ""}`}
        type={isVisible ? "text" : "password"}
      />
      <button
        aria-label={label}
        className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        onClick={() => setIsVisible((visible) => !visible)}
        title={label}
        type="button"
      >
        {isVisible ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
      </button>
    </div>
  );
}
