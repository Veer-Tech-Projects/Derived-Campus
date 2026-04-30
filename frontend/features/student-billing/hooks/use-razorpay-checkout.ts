"use client";

import { useCallback, useEffect, useRef, useState } from "react";

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => {
      open: () => void;
      on: (eventName: string, callback: () => void) => void;
    };
  }
}

const RAZORPAY_CHECKOUT_SCRIPT_URL =
  "https://checkout.razorpay.com/v1/checkout.js";

type OpenRazorpayCheckoutInput = {
  key: string;
  orderId: string;
  amountMinor: number;
  currencyCode: string;
  merchantOrderRef: string;
  prefillName?: string | null;
  prefillEmail?: string | null;
  onPaymentCompleted?: () => void;
  onDismiss?: () => void;
  onPaymentFailed?: () => void;
};

type UseRazorpayCheckoutResult = {
  isScriptLoading: boolean;
  isScriptReady: boolean;
  scriptError: Error | null;
  ensureScriptLoaded: () => Promise<boolean>;
  openCheckout: (input: OpenRazorpayCheckoutInput) => Promise<boolean>;
};

export function useRazorpayCheckout(): UseRazorpayCheckoutResult {
  const [isScriptLoading, setIsScriptLoading] = useState(false);
  const [isScriptReady, setIsScriptReady] = useState(false);
  const [scriptError, setScriptError] = useState<Error | null>(null);

  const pendingPromiseRef = useRef<Promise<boolean> | null>(null);

  const ensureScriptLoaded = useCallback(async (): Promise<boolean> => {
    if (typeof window === "undefined") {
      setScriptError(new Error("Razorpay checkout is not available on the server."));
      return false;
    }

    if (window.Razorpay) {
      setIsScriptReady(true);
      setScriptError(null);
      return true;
    }

    if (pendingPromiseRef.current) {
      return pendingPromiseRef.current;
    }

    setIsScriptLoading(true);
    setScriptError(null);

    pendingPromiseRef.current = new Promise<boolean>((resolve) => {
      const existingScript = document.querySelector<HTMLScriptElement>(
        `script[src="${RAZORPAY_CHECKOUT_SCRIPT_URL}"]`,
      );

      const finalizeSuccess = () => {
        setIsScriptLoading(false);
        setIsScriptReady(true);
        setScriptError(null);
        pendingPromiseRef.current = null;
        resolve(true);
      };

      const finalizeFailure = () => {
        const error = new Error("Failed to load Razorpay checkout script.");
        setIsScriptLoading(false);
        setIsScriptReady(false);
        setScriptError(error);
        pendingPromiseRef.current = null;
        resolve(false);
      };

      if (existingScript) {
        if (window.Razorpay) {
          finalizeSuccess();
          return;
        }

        existingScript.addEventListener("load", finalizeSuccess, { once: true });
        existingScript.addEventListener("error", finalizeFailure, { once: true });
        return;
      }

      const script = document.createElement("script");
      script.src = RAZORPAY_CHECKOUT_SCRIPT_URL;
      script.async = true;
      script.onload = finalizeSuccess;
      script.onerror = finalizeFailure;

      document.body.appendChild(script);
    });

    return pendingPromiseRef.current;
  }, []);

  const openCheckout = useCallback(
    async (input: OpenRazorpayCheckoutInput): Promise<boolean> => {
      const ready = await ensureScriptLoaded();
      if (!ready || typeof window === "undefined" || !window.Razorpay) {
        return false;
      }

      const razorpay = new window.Razorpay({
        key: input.key,
        order_id: input.orderId,
        amount: input.amountMinor,
        currency: input.currencyCode,
        name: "Derived Campus",
        description: "Secure student credit purchase",
        handler: () => {
          input.onPaymentCompleted?.();
        },
        modal: {
          ondismiss: () => {
            input.onDismiss?.();
          },
        },
        notes: {
          merchant_order_ref: input.merchantOrderRef,
        },
        prefill: {
          name: input.prefillName ?? undefined,
          email: input.prefillEmail ?? undefined,
        },
        theme: {
          color: "#8e5faf",
        },
      });

      razorpay.on("payment.failed", () => {
        input.onPaymentFailed?.();
      });

      razorpay.open();
      return true;
    },
    [ensureScriptLoaded],
  );

  useEffect(() => {
    return () => {
      pendingPromiseRef.current = null;
    };
  }, []);

  return {
    isScriptLoading,
    isScriptReady,
    scriptError,
    ensureScriptLoaded,
    openCheckout,
  };
}