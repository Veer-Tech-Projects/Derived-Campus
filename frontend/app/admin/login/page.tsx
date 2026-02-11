"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/components/providers/auth-provider";
import { ShieldCheck, Loader2, Lock, AlertTriangle, Clock, Ban } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // --- SECURITY STATE ---
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lockoutTime, setLockoutTime] = useState<Date | null>(null);
  const [timerDisplay, setTimerDisplay] = useState("00:00");

  // 1. PERSISTENCE CHECK (Restore Lock on Refresh)
  useEffect(() => {
    const storedLockout = localStorage.getItem("admin_lockout_expiry");
    if (storedLockout) {
      const expiry = new Date(storedLockout);
      if (expiry.getTime() > new Date().getTime()) {
        setLockoutTime(expiry);
        // Calculate initial display immediately so it doesn't blink "00:00"
        const now = new Date().getTime();
        const distance = expiry.getTime() - now;
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        setTimerDisplay(`${minutes}:00`); // Approximation until next tick
      } else {
        // Clean up expired lock
        localStorage.removeItem("admin_lockout_expiry");
      }
    }
  }, []);

  // 2. REAL-TIME TICKER
  useEffect(() => {
    if (!lockoutTime) return;

    const timer = setInterval(() => {
      const now = new Date().getTime();
      const distance = lockoutTime.getTime() - now;

      if (distance < 0) {
        // Time is up! Unlock the UI
        setLockoutTime(null); 
        setErrorMessage(null); 
        localStorage.removeItem("admin_lockout_expiry"); // <--- Clear Storage
        clearInterval(timer);
      } else {
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);
        setTimerDisplay(`${minutes}:${seconds.toString().padStart(2, '0')}`);
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [lockoutTime]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await login(username, password);
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Authentication failed";
      
      // 3. DETECT & SAVE LOCKOUT
      const lockoutMatch = msg.match(/Try again in (\d+) minutes/);
      if (lockoutMatch) {
        const minutes = parseInt(lockoutMatch[1], 10);
        // Add 1 minute buffer to match backend logic
        const expiry = new Date(new Date().getTime() + minutes * 60000 + 1000); 
        
        setLockoutTime(expiry);
        setTimerDisplay(`${minutes}:00`);
        
        // <--- SAVE TO STORAGE
        localStorage.setItem("admin_lockout_expiry", expiry.toISOString());
      }

      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isLocked = !!lockoutTime;

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden relative z-10">
        
        {/* --- HEADER --- */}
        <div className={`p-8 text-center transition-colors duration-500 ${isLocked ? 'bg-red-900' : 'bg-slate-900'}`}>
          <div className={`mx-auto w-16 h-16 rounded-full flex items-center justify-center mb-4 ring-4 transition-all duration-500 ${isLocked ? 'bg-red-800 ring-red-700' : 'bg-emerald-600 ring-emerald-900/50'}`}>
            {isLocked ? (
              <Ban className="text-white w-8 h-8 animate-pulse" />
            ) : (
              <ShieldCheck className="text-white w-9 h-9" />
            )}
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            {isLocked ? "SECURITY LOCKOUT" : "Command Center"}
          </h1>
          <p className={`text-sm mt-2 font-medium ${isLocked ? 'text-red-200' : 'text-slate-400'}`}>
            {isLocked ? "Too many failed attempts." : "Restricted Access. Authorization Required."}
          </p>
        </div>

        {/* --- FORM BODY --- */}
        <div className="p-8 bg-white">
          
          {/* Lockout Timer Display */}
          {isLocked && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex flex-col items-center justify-center text-red-800 animate-in fade-in zoom-in duration-300">
              <span className="text-xs font-bold uppercase tracking-wider mb-1">System Locked For</span>
              <div className="flex items-center gap-2 text-4xl font-mono font-bold">
                <Clock className="w-8 h-8" />
                {timerDisplay}
              </div>
            </div>
          )}

          {/* Warning / Error Message */}
          {!isLocked && errorMessage && (
            <div className={`mb-6 p-3 rounded-lg text-sm flex items-start gap-3 border ${
              errorMessage.includes("Warning") 
                ? "bg-amber-50 text-amber-800 border-amber-200" 
                : "bg-red-50 text-red-700 border-red-200"
            }`}>
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <span className="font-medium">{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">Operative ID</label>
              <input
                type="text"
                required
                disabled={isLocked || isSubmitting}
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:bg-white focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                placeholder="Enter username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">Passcode</label>
              <input
                type="password"
                required
                disabled={isLocked || isSubmitting}
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:bg-white focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting || isLocked}
              className={`w-full py-3 rounded-lg font-bold text-sm uppercase tracking-wide flex items-center justify-center transition-all shadow-sm 
                ${isLocked 
                  ? "bg-slate-300 text-slate-500 cursor-not-allowed" 
                  : "bg-slate-900 text-white hover:bg-slate-800 hover:shadow-lg active:scale-[0.98]"
                }`}
            >
              {isSubmitting ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Verifying Credentials...</>
              ) : isLocked ? (
                <><Lock className="w-4 h-4 mr-2" /> Access Suspended</>
              ) : (
                <><ShieldCheck className="w-4 h-4 mr-2" /> Authenticate</>
              )}
            </button>
          </form>
        </div>
        
        {/* --- FOOTER --- */}
        <div className="bg-slate-50 px-6 py-4 border-t border-slate-100 flex justify-between items-center text-xs text-slate-400 font-medium">
          <span>Secure Enclave v2.4</span>
          <div className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${isLocked ? "bg-red-500 animate-pulse" : "bg-emerald-500"}`}></div>
            {isLocked ? "SYSTEM LOCKED" : "MONITORING ACTIVE"}
          </div>
        </div>
      </div>
    </div>
  );
}