import { createContext, useContext } from 'react';
import type { UserContextType } from '../types';

/** React context that holds the currently signed-in user and auth helpers. */
export const UserContext = createContext<UserContextType | undefined>(undefined);

/**
 * Hook that returns the current user context.
 *
 * Must be called from a component tree wrapped in `UserProvider`
 * (see `useUser.tsx`). Throws if called outside the provider so that
 * missing-provider bugs are caught early at runtime.
 *
 * @returns `UserContextType` — `{ user, setUser, logout }`
 * @throws Error if called outside of a `UserProvider`
 */
export const useUser = (): UserContextType => {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};
