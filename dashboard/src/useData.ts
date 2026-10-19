import { useCallback, useEffect, useState } from "react";

export interface Data<T> {
  data: T | undefined;
  error: string | undefined;
  reload: () => void;
}

export function useData<T>(
  load: () => Promise<T>,
  everyMs: number | null,
): Data<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string>();
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => {
    setTick((n) => n + 1);
  }, []);

  useEffect(() => {
    let live = true;
    load().then(
      (value) => {
        if (!live) return;
        setData(value);
        setError(undefined);
      },
      (reason: unknown) => {
        if (live) setError(reason instanceof Error ? reason.message : "Failed");
      },
    );
    return () => {
      live = false;
    };
  }, [load, tick]);

  useEffect(() => {
    if (everyMs === null) return;
    const timer = setInterval(reload, everyMs);
    return () => {
      clearInterval(timer);
    };
  }, [everyMs, reload]);

  return { data, error, reload };
}
