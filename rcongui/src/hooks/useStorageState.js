import siteConfig from '@/config/siteConfig';
import {useEffect, useState} from "react";
import deepmerge from 'lodash/merge';
import { browserStorage } from '@/utils/browser-storage';

const STORAGE_VERSION = '1.0'; // Define current version
const prefix = siteConfig.appName + '.';
const withPrefix = (key) => prefix + key;

const getItem = (key) => {
  try {
    const storedValue = browserStorage.getItem(withPrefix(key));
    if (!storedValue) return null;
    
    const parsed = JSON.parse(storedValue);
    
    // Check if stored data has version information
    if (!parsed._version) {
      // No version - treat as legacy data
      browserStorage.removeItem(withPrefix(key));
      return null;
    }

    // Version mismatch
    if (parsed._version !== STORAGE_VERSION) {
      console.info(`
        Storage version mismatch for ${key}.\n
        Stored: ${parsed._version}, Current: ${STORAGE_VERSION}\n
        Migrating data...
      `);
      browserStorage.removeItem(withPrefix(key));
      return null;
    }

    return parsed.data;
  } catch (error) {
    // Storage itself may be unavailable; a second access here would throw
    // again and prevent the page from mounting.
    console.warn(`Storage read failed for ${key}: ${error.message}`);
    try {
      browserStorage.removeItem(withPrefix(key));
    } catch {
      // The page can still use its default value without persistent storage.
    }
    return null;
  }
};

const setItem = (key, value) => {
  const storageData = {
    _version: STORAGE_VERSION,
    data: value
  };
  try {
    browserStorage.setItem(withPrefix(key), JSON.stringify(storageData));
  } catch (error) {
    // React retains this preference for the current visit only.
    console.warn(`Storage write failed for ${key}: ${error.message}`);
  }
};

export const useStorageState = (key, initialState) => {
  const [value, setValue] = useState(() => {
    const storedValue = getItem(key);
    
    if (storedValue && typeof initialState === 'object') {
      // Deep merge stored value with initial state
      return deepmerge({}, initialState, storedValue);
    }
    
    return storedValue ?? initialState;
  });

  useEffect(() => {
    setItem(key, value);
  }, [key, value]);

  return [value, setValue];
};
