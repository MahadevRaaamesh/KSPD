import { createContext, useContext } from 'react';

/**
 * Session context: { session, loginSession(session), logout() }.
 * Kept out of App.jsx so that file only exports its component
 * (keeps react-refresh able to hot-reload the router).
 */
export const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);
