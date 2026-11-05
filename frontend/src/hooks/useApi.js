import { useCallback, useEffect, useRef, useState } from "react";

export function useApi(request, dependencies = []) {
  const [data, setData] = useState(null);
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const requestSequence = useRef(0);

  const run = useCallback(async () => {
    const sequence = ++requestSequence.current;
    setLoading(true);
    setError(null);
    try {
      const response = await request();
      if (sequence === requestSequence.current) {
        setData(response.data);
        setMeta(response.meta ?? null);
      }
      return response;
    } catch (requestError) {
      if (sequence === requestSequence.current) {
        setError(requestError);
      }
      return null;
    } finally {
      if (sequence === requestSequence.current) {
        setLoading(false);
      }
    }
  }, dependencies);

  useEffect(() => {
    void run();
    return () => {
      requestSequence.current += 1;
    };
  }, [run]);

  return { data, setData, meta, error, loading, reload: run };
}