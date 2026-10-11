// Share overlapping reads and cancel work that belongs to an abandoned view.
// Callers still fence commits by company: a server may finish after fetch aborts.
export function createReadLane() {
  let current = null;
  return {
    read(key, fetcher) {
      if (current?.key === key) return current.promise;
      current?.controller.abort();
      const controller = new AbortController();
      const entry = { key, controller };
      entry.promise = Promise.resolve()
        .then(() => {
          controller.signal.throwIfAborted();
          return fetcher(controller.signal);
        })
        .finally(() => {
          if (current === entry) current = null;
        });
      current = entry;
      return entry.promise;
    },
    cancel() {
      current?.controller.abort();
      current = null;
    },
  };
}
