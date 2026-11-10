'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from './api';

interface AuthContextType {
  token: string | null;
  workerName: string | null;
  workerId: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (phone: string, pin: string) => Promise<void>;
  register: (name: string, phone: string, pin: string, language?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [workerName, setWorkerName] = useState<string | null>(null);
  const [workerId, setWorkerId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    queueMicrotask(() => {
      if (!mounted) return;
      const savedToken = localStorage.getItem('mazdoor_token');
      const savedName = localStorage.getItem('mazdoor_name');
      const savedId = localStorage.getItem('mazdoor_worker_id');

      if (savedToken) {
        setToken(savedToken);
        setWorkerName(savedName || 'मज़दूर साथी');
        setWorkerId(savedId);
      }
      setIsLoading(false);
    });
    return () => {
      mounted = false;
    };
  }, []);

  const login = async (phone: string, pin: string) => {
    const res = await api.login({ phone, pin });
    setToken(res.access_token);
    setWorkerName(res.name);
    setWorkerId(res.worker_id);
    localStorage.setItem('mazdoor_token', res.access_token);
    localStorage.setItem('mazdoor_name', res.name);
    localStorage.setItem('mazdoor_worker_id', res.worker_id);
  };

  const register = async (name: string, phone: string, pin: string, language: string = 'hi') => {
    const res = await api.register({ name, phone, pin, preferred_language: language });
    setToken(res.access_token);
    setWorkerName(res.name);
    setWorkerId(res.worker_id);
    localStorage.setItem('mazdoor_token', res.access_token);
    localStorage.setItem('mazdoor_name', res.name);
    localStorage.setItem('mazdoor_worker_id', res.worker_id);
  };

  const logout = () => {
    setToken(null);
    setWorkerName(null);
    setWorkerId(null);
    localStorage.removeItem('mazdoor_token');
    localStorage.removeItem('mazdoor_name');
    localStorage.removeItem('mazdoor_worker_id');
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        workerName,
        workerId,
        isAuthenticated: !!token,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
