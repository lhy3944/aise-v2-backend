import { useSyncExternalStore } from 'react';

type PersistStore = {
  persist: {
    onFinishHydration: (fn: () => void) => () => void;
    hasHydrated: () => boolean;
  };
};

export function useStoreHydration(...stores: PersistStore[]) {
  return useSyncExternalStore(
    (callback) => {
      const unsubs = stores.map((store) => store.persist.onFinishHydration(callback));
      return () => unsubs.forEach((unsub) => unsub());
    },
    () => stores.every((store) => store.persist.hasHydrated()),
    () => false,
  );
}
