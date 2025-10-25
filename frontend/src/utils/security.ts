/**
 * Frontend security utilities
 */

import DOMPurify from "dompurify";

/**
 * Sanitize user input to prevent XSS attacks
 */
export const sanitizeInput = (input: string): string => {
  return DOMPurify.sanitize(input, {
    ALLOWED_TAGS: [],
    ALLOWED_ATTR: [],
  });
};

/**
 * Sanitize HTML content for display
 */
export const sanitizeHTML = (html: string): string => {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ["b", "i", "em", "strong", "p", "br"],
    ALLOWED_ATTR: [],
  });
};

/**
 * Validate email format
 */
export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Validate password strength
 */
export const validatePassword = (
  password: string
): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (password.length < 8) {
    errors.push("Password must be at least 8 characters long");
  }

  if (!/[A-Z]/.test(password)) {
    errors.push("Password must contain at least one uppercase letter");
  }

  if (!/[a-z]/.test(password)) {
    errors.push("Password must contain at least one lowercase letter");
  }

  if (!/\d/.test(password)) {
    errors.push("Password must contain at least one number");
  }

  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push("Password must contain at least one special character");
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
};

/**
 * Generate secure random string
 */
export const generateSecureToken = (length: number = 32): string => {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return Array.from(array, (byte) => byte.toString(16).padStart(2, "0")).join(
    ""
  );
};

/**
 * Secure token storage
 */
export class SecureTokenStorage {
  private static readonly TOKEN_KEY = "auth_token";
  private static readonly REFRESH_TOKEN_KEY = "refresh_token";

  static setToken(token: string): void {
    // In production, use secure storage or httpOnly cookies
    sessionStorage.setItem(this.TOKEN_KEY, token);
  }

  static getToken(): string | null {
    return sessionStorage.getItem(this.TOKEN_KEY);
  }

  static removeToken(): void {
    sessionStorage.removeItem(this.TOKEN_KEY);
    sessionStorage.removeItem(this.REFRESH_TOKEN_KEY);
  }

  static setRefreshToken(token: string): void {
    sessionStorage.setItem(this.REFRESH_TOKEN_KEY, token);
  }

  static getRefreshToken(): string | null {
    return sessionStorage.getItem(this.REFRESH_TOKEN_KEY);
  }
}

/**
 * CSRF protection
 */
export class CSRFProtection {
  private static readonly CSRF_TOKEN_KEY = "csrf_token";

  static generateToken(): string {
    const token = generateSecureToken(32);
    sessionStorage.setItem(this.CSRF_TOKEN_KEY, token);
    return token;
  }

  static getToken(): string | null {
    return sessionStorage.getItem(this.CSRF_TOKEN_KEY);
  }

  static validateToken(token: string): boolean {
    const storedToken = this.getToken();
    return storedToken === token;
  }
}

/**
 * Input validation
 */
export class InputValidator {
  static validateAmount(amount: number): { isValid: boolean; error?: string } {
    if (isNaN(amount) || !isFinite(amount)) {
      return { isValid: false, error: "Amount must be a valid number" };
    }

    if (amount <= 0) {
      return { isValid: false, error: "Amount must be greater than 0" };
    }

    if (amount > 100000) {
      return { isValid: false, error: "Amount cannot exceed $100,000" };
    }

    // Check for reasonable decimal places
    const decimalPlaces = (amount.toString().split(".")[1] || "").length;
    if (decimalPlaces > 2) {
      return {
        isValid: false,
        error: "Amount cannot have more than 2 decimal places",
      };
    }

    return { isValid: true };
  }

  static validateUsername(username: string): {
    isValid: boolean;
    error?: string;
  } {
    if (!username || username.trim().length === 0) {
      return { isValid: false, error: "Username is required" };
    }

    if (username.length < 3) {
      return {
        isValid: false,
        error: "Username must be at least 3 characters long",
      };
    }

    if (username.length > 20) {
      return { isValid: false, error: "Username cannot exceed 20 characters" };
    }

    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      return {
        isValid: false,
        error: "Username can only contain letters, numbers, and underscores",
      };
    }

    return { isValid: true };
  }
}

/**
 * Security event logging
 */
export class SecurityLogger {
  static logSecurityEvent(event: string, details: any): void {
    console.warn(`SECURITY_EVENT: ${event}`, details);

    // In production, send to security monitoring service
    if (process.env.NODE_ENV === "production") {
      // Send to security monitoring service
      fetch("/api/v1/security/events", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          event,
          details,
          timestamp: new Date().toISOString(),
          userAgent: navigator.userAgent,
          url: window.location.href,
        }),
      }).catch((error) => {
        console.error("Failed to log security event:", error);
      });
    }
  }

  static logSuspiciousActivity(activity: string, details: any): void {
    this.logSecurityEvent("suspicious_activity", {
      activity,
      details,
      severity: "high",
    });
  }
}

/**
 * Rate limiting
 */
export class RateLimiter {
  private static limits: Map<string, { count: number; resetTime: number }> =
    new Map();

  static checkLimit(
    key: string,
    maxRequests: number,
    windowMs: number
  ): boolean {
    const now = Date.now();
    const limit = this.limits.get(key);

    if (!limit || now > limit.resetTime) {
      this.limits.set(key, { count: 1, resetTime: now + windowMs });
      return true;
    }

    if (limit.count >= maxRequests) {
      return false;
    }

    limit.count++;
    return true;
  }

  static resetLimit(key: string): void {
    this.limits.delete(key);
  }
}
