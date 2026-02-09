# Custom Hooks Documentation

This document describes all custom hooks available in the Employee Attendance Admin Dashboard application.

## Overview

Custom hooks provide reusable logic that can be shared across components, improving code reusability, maintainability, and performance.

## Available Hooks

### 1. `useDebounce`

Debounces a value, useful for search inputs and API calls.

**Location:** `src/hooks/useDebounce.js`

**Usage:**
```javascript
import { useDebounce } from '../hooks';

const MyComponent = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearchTerm = useDebounce(searchTerm, 500);

  useEffect(() => {
    // This will only run after user stops typing for 500ms
    if (debouncedSearchTerm) {
      performSearch(debouncedSearchTerm);
    }
  }, [debouncedSearchTerm]);

  return (
    <input
      value={searchTerm}
      onChange={(e) => setSearchTerm(e.target.value)}
      placeholder="Search..."
    />
  );
};
```

**Parameters:**
- `value` (any): The value to debounce
- `delay` (number, optional): Delay in milliseconds (default: 500)

**Returns:** The debounced value

---

### 2. `useLocalStorage`

Syncs state with localStorage, automatically handling JSON serialization.

**Location:** `src/hooks/useLocalStorage.js`

**Usage:**
```javascript
import { useLocalStorage } from '../hooks';

const MyComponent = () => {
  const [userPreferences, setUserPreferences] = useLocalStorage('userPrefs', {
    theme: 'light',
    language: 'en'
  });

  const toggleTheme = () => {
    setUserPreferences(prev => ({
      ...prev,
      theme: prev.theme === 'light' ? 'dark' : 'light'
    }));
  };

  return <div>Current theme: {userPreferences.theme}</div>;
};
```

**Parameters:**
- `key` (string): The localStorage key
- `initialValue` (any): Initial value if key doesn't exist

**Returns:** `[storedValue, setValue]` - Similar to useState

**Features:**
- Automatic JSON serialization/deserialization
- Listens for changes from other tabs/windows
- Error handling

---

### 3. `useApi`

Makes API calls with loading, error, and data states. Automatically handles cleanup and prevents race conditions.

**Location:** `src/hooks/useApi.js`

**Usage:**
```javascript
import { useApi } from '../hooks';
import { usersAPI } from '../services/api';

// Call immediately on mount
const MyComponent = () => {
  const { data, loading, error, execute, reset } = useApi(
    () => usersAPI.getUsers(),
    [],
    true // Call immediately
  );

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return <div>{data.length} users found</div>;
};

// Or call manually
const UserDetails = ({ userId }) => {
  const { data, loading, error, execute } = useApi(
    () => usersAPI.getUser(userId),
    null
  );

  useEffect(() => {
    if (userId) {
      execute();
    }
  }, [userId, execute]);

  // ... rest of component
};
```

**Parameters:**
- `apiFunction` (function): The API function to call
- `initialData` (any, optional): Initial data value (default: null)
- `immediate` (boolean, optional): Whether to call API immediately (default: false)

**Returns:**
- `data`: The response data
- `loading`: Loading state
- `error`: Error message or null
- `execute`: Function to manually trigger API call
- `reset`: Function to reset state

**Features:**
- Automatic cleanup on unmount
- Prevents race conditions
- AbortController support
- Error handling

---

### 4. `usePagination`

Handles pagination logic for arrays of items.

**Location:** `src/hooks/usePagination.js`

**Usage:**
```javascript
import { usePagination } from '../hooks';

const UserList = ({ users }) => {
  const {
    currentItems,
    totalPages,
    currentPage,
    itemsPerPage,
    setPage,
    setItemsPerPage,
    nextPage,
    previousPage,
    hasNextPage,
    hasPreviousPage
  } = usePagination(users, 25);

  return (
    <div>
      {currentItems.map(user => (
        <div key={user.id}>{user.name}</div>
      ))}
      
      <div>
        <button onClick={previousPage} disabled={!hasPreviousPage}>
          Previous
        </button>
        <span>Page {currentPage} of {totalPages}</span>
        <button onClick={nextPage} disabled={!hasNextPage}>
          Next
        </button>
      </div>
    </div>
  );
};
```

**Parameters:**
- `items` (array): Array of items to paginate
- `initialItemsPerPage` (number, optional): Initial items per page (default: 10)

**Returns:**
- `currentItems`: Items for current page
- `totalItems`: Total number of items
- `totalPages`: Total number of pages
- `currentPage`: Current page number
- `itemsPerPage`: Items per page
- `startIndex`: 1-based start index
- `endIndex`: 1-based end index
- `hasNextPage`: Boolean
- `hasPreviousPage`: Boolean
- `setPage`: Function to go to specific page
- `setItemsPerPage`: Function to change items per page
- `nextPage`: Function to go to next page
- `previousPage`: Function to go to previous page
- `reset`: Function to reset to first page

---

### 5. `useWindowSize`

Tracks window size for responsive design.

**Location:** `src/hooks/useWindowSize.js`

**Usage:**
```javascript
import { useWindowSize } from '../hooks';

const ResponsiveComponent = () => {
  const { width, height } = useWindowSize();
  const isMobile = width < 768;
  const isTablet = width >= 768 && width < 1024;

  return (
    <div>
      {isMobile ? (
        <MobileLayout />
      ) : isTablet ? (
        <TabletLayout />
      ) : (
        <DesktopLayout />
      )}
    </div>
  );
};
```

**Returns:**
- `width`: Window width in pixels
- `height`: Window height in pixels

---

### 6. `useClickOutside`

Detects clicks outside an element, useful for closing modals and dropdowns.

**Location:** `src/hooks/useClickOutside.js`

**Usage:**
```javascript
import { useClickOutside } from '../hooks';

const Dropdown = () => {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useClickOutside(() => {
    setIsOpen(false);
  });

  return (
    <div ref={ref}>
      <button onClick={() => setIsOpen(!isOpen)}>Toggle</button>
      {isOpen && <div>Dropdown content</div>}
    </div>
  );
};
```

**Parameters:**
- `handler` (function): Function to call when click outside is detected
- `enabled` (boolean, optional): Whether the hook is enabled (default: true)

**Returns:** Ref to attach to the element

---

### 7. `useInterval`

Custom setInterval hook with proper cleanup.

**Location:** `src/hooks/useInterval.js`

**Usage:**
```javascript
import { useInterval } from '../hooks';

const PollingComponent = () => {
  const [count, setCount] = useState(0);
  const [isRunning, setIsRunning] = useState(true);

  useInterval(() => {
    setCount(count + 1);
  }, isRunning ? 1000 : null); // null pauses the interval

  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setIsRunning(!isRunning)}>
        {isRunning ? 'Pause' : 'Resume'}
      </button>
    </div>
  );
};
```

**Parameters:**
- `callback` (function): Function to call on each interval
- `delay` (number|null): Delay in milliseconds (null to pause)

**Features:**
- Automatically cleans up on unmount
- Can be paused by passing null
- Proper cleanup handling

---

### 8. `useMediaQuery`

Matches media queries for responsive design.

**Location:** `src/hooks/useMediaQuery.js`

**Usage:**
```javascript
import { useMediaQuery } from '../hooks';

const ResponsiveComponent = () => {
  const isMobile = useMediaQuery('(max-width: 767px)');
  const isTablet = useMediaQuery('(min-width: 768px) and (max-width: 1023px)');
  const isDesktop = useMediaQuery('(min-width: 1024px)');

  return (
    <div>
      {isMobile && <MobileView />}
      {isTablet && <TabletView />}
      {isDesktop && <DesktopView />}
    </div>
  );
};
```

**Parameters:**
- `query` (string): Media query string (e.g., '(min-width: 768px)')

**Returns:** Boolean indicating if media query matches

---

### 9. `usePreventRefresh`

Prevents page refresh and navigation (existing hook).

**Location:** `src/hooks/usePreventRefresh.js`

**Usage:**
```javascript
import { usePreventRefresh } from '../hooks';

const FormComponent = () => {
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  
  usePreventRefresh(
    hasUnsavedChanges,
    'You have unsaved changes. Are you sure you want to leave?'
  );

  // ... rest of component
};
```

**Parameters:**
- `enabled` (boolean): Whether to enable refresh prevention
- `message` (string, optional): Custom message
- `onBeforeLeave` (function, optional): Callback function

**Returns:** `{ enable, disable, isEnabled }`

---

## Importing Hooks

### Individual Imports
```javascript
import { useDebounce, useLocalStorage, useApi } from '../hooks';
```

### Default Imports
```javascript
import useDebounce from '../hooks/useDebounce';
import useLocalStorage from '../hooks/useLocalStorage';
```

### From Index
```javascript
import {
  useDebounce,
  useLocalStorage,
  useApi,
  usePagination,
  useWindowSize,
  useClickOutside,
  useInterval,
  useMediaQuery,
  usePreventRefresh
} from '../hooks';
```

---

## Best Practices

1. **Use `useDebounce` for search inputs** - Reduces API calls and improves performance
2. **Use `useApi` for API calls** - Provides consistent loading/error handling
3. **Use `usePagination` for large lists** - Improves performance and UX
4. **Use `useClickOutside` for modals** - Better UX for closing modals
5. **Use `useInterval` instead of setInterval** - Proper cleanup handling
6. **Use `useMediaQuery` for responsive design** - More reliable than window size checks

---

## Performance Benefits

- **Reduced re-renders**: Hooks are optimized to prevent unnecessary re-renders
- **Proper cleanup**: All hooks handle cleanup on unmount
- **Memory efficiency**: Prevents memory leaks with proper cleanup
- **Code reusability**: Share logic across components
- **Type safety**: Consistent API across hooks

---

## Examples

### Search with Debouncing
```javascript
const SearchUsers = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearchTerm = useDebounce(searchTerm, 500);
  const { data, loading } = useApi(
    () => usersAPI.searchUsers(debouncedSearchTerm),
    [],
    false
  );

  useEffect(() => {
    if (debouncedSearchTerm) {
      execute();
    }
  }, [debouncedSearchTerm]);

  return (
    <input
      value={searchTerm}
      onChange={(e) => setSearchTerm(e.target.value)}
    />
  );
};
```

### Paginated List
```javascript
const UserList = ({ users }) => {
  const {
    currentItems,
    totalPages,
    currentPage,
    setPage,
    nextPage,
    previousPage
  } = usePagination(users, 25);

  return (
    <>
      {currentItems.map(user => <UserCard key={user.id} user={user} />)}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={setPage}
        onNext={nextPage}
        onPrevious={previousPage}
      />
    </>
  );
};
```

---

*Last Updated: $(date)*
*Hooks created by: AI Assistant*
