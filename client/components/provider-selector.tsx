"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface Props {
  providers: Record<string, string[]>;
  value: string; // "provider/model"
  onChange: (provider: string, model: string) => void;
  disabled?: boolean;
}

export function ProviderSelector({ providers, value, onChange, disabled }: Props) {
  const options = Object.entries(providers).flatMap(([provider, models]) =>
    models.map((model) => ({ key: `${provider}/${model}`, provider, model })),
  );

  return (
    <Select
      value={value}
      onValueChange={(v) => {
        const [provider, ...rest] = v.split("/");
        onChange(provider, rest.join("/"));
      }}
      disabled={disabled}
    >
      <SelectTrigger className="h-7 w-auto gap-1.5 border-none bg-transparent px-2 text-xs font-medium shadow-none hover:bg-muted focus:ring-0">
        <SelectValue />
      </SelectTrigger>
      <SelectContent align="start">
        {options.map(({ key, provider, model }) => (
          <SelectItem key={key} value={key} className="text-xs">
            <span className="capitalize">{provider}</span>
            <span className="ml-1.5 text-muted-foreground">/ {model}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
