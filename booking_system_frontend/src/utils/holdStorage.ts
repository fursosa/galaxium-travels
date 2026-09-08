import type { StoredHold } from '../types';

/**
 * localStorage key prefix for persisted hold data.
 * Full key format: `galaxium_holds_{userId}`
 */
const KEY_PREFIX = 'galaxium_holds_';

/**
 * Retrieve all persisted holds for a given user from localStorage.
 *
 * Holds are stored so they survive page refreshes and appear in the
 * My Bookings view before the user confirms or the hold expires.
 * Returns an empty array if nothing is stored or the data is corrupted.
 *
 * @param userId - The currently signed-in user's ID.
 * @returns Array of `StoredHold` objects, or `[]` on parse failure.
 */
export const getStoredHolds = (userId: number): StoredHold[] => {
  try {
    const data = localStorage.getItem(`${KEY_PREFIX}${userId}`);
    if (!data) return [];
    return JSON.parse(data) as StoredHold[];
  } catch {
    return [];
  }
};

/**
 * Persist a hold for a user, replacing any existing entry with the same `holdId`.
 *
 * @param userId - The currently signed-in user's ID.
 * @param hold - The hold to store or update.
 */
export const storeHold = (userId: number, hold: StoredHold): void => {
  const holds = getStoredHolds(userId);
  const updated = [...holds.filter((h) => h.holdId !== hold.holdId), hold];
  localStorage.setItem(`${KEY_PREFIX}${userId}`, JSON.stringify(updated));
};

/**
 * Remove a specific hold from localStorage.
 *
 * Called after a hold is confirmed, released, or found to be expired.
 *
 * @param userId - The currently signed-in user's ID.
 * @param holdId - The ID of the hold to remove.
 */
export const removeHold = (userId: number, holdId: string): void => {
  const holds = getStoredHolds(userId);
  const updated = holds.filter((h) => h.holdId !== holdId);
  localStorage.setItem(`${KEY_PREFIX}${userId}`, JSON.stringify(updated));
};

// Made with Bob
