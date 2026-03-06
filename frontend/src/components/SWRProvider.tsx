"use client";

import { SWRConfig } from "swr";
import type { ReactNode } from "react";

export function SWRProvider({ children }: { children: ReactNode }) {
  return (
    <SWRConfig
      value={{
        dedupingInterval: 60000,
        focusThrottleInterval: 30000,
        errorRetryCount: 3,
        errorRetryInterval: 5000,
        revalidateOnFocus: false,
      }}
    >
      {children}
    </SWRConfig>
  );
}
