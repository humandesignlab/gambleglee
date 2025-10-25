import { useState, useEffect } from 'react';

interface LocationData {
  country: string;
  country_name: string;
  region: string;
  city: string;
  compliance_status: 'allowed' | 'restricted' | 'blocked';
  payment_processor: string;
  payment_methods: string[];
  currency: string;
}

interface ComplianceRequirements {
  kyc_required: boolean;
  age_verification: boolean;
  tax_collection: boolean;
  deposit_limits: {
    daily: number;
    weekly: number;
    monthly: number;
  };
  withdrawal_limits: {
    daily: number;
    weekly: number;
    monthly: number;
  };
  currency: string;
}

export const useLocation = () => {
  const [location, setLocation] = useState<LocationData | null>(null);
  const [compliance, setCompliance] = useState<ComplianceRequirements | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const detectLocation = async () => {
      try {
        setIsLoading(true);
        
        // Get location from backend headers (set by middleware)
        const response = await fetch('/api/v1/location', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          const data = await response.json();
          setLocation(data.location);
          setCompliance(data.compliance_requirements);
        } else {
          // Fallback to browser geolocation API
          await detectLocationFallback();
        }
      } catch (err) {
        console.error('Location detection failed:', err);
        setError('Failed to detect location');
        // Set default US location
        setLocation({
          country: 'US',
          country_name: 'United States',
          region: '',
          city: '',
          compliance_status: 'allowed',
          payment_processor: 'stripe',
          payment_methods: ['card', 'ach', 'bank_transfer'],
          currency: 'USD'
        });
        setCompliance({
          kyc_required: true,
          age_verification: true,
          tax_collection: true,
          deposit_limits: { daily: 1000, weekly: 5000, monthly: 20000 },
          withdrawal_limits: { daily: 5000, weekly: 10000, monthly: 50000 },
          currency: 'USD'
        });
      } finally {
        setIsLoading(false);
      }
    };

    detectLocation();
  }, []);

  const detectLocationFallback = async () => {
    try {
      // Use browser's geolocation API as fallback
      if (navigator.geolocation) {
        const position = await new Promise<GeolocationPosition>((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            timeout: 5000,
            enableHighAccuracy: false
          });
        });

        // Reverse geocoding would be needed here
        // For now, default to US
        setLocation({
          country: 'US',
          country_name: 'United States',
          region: '',
          city: '',
          compliance_status: 'allowed',
          payment_processor: 'stripe',
          payment_methods: ['card', 'ach', 'bank_transfer'],
          currency: 'USD'
        });
      }
    } catch (err) {
      console.error('Geolocation fallback failed:', err);
    }
  };

  const getPaymentMethodLabel = (method: string) => {
    const labels: Record<string, string> = {
      'card': 'Credit/Debit Card',
      'ach': 'Bank Transfer (ACH)',
      'bank_transfer': 'Bank Transfer',
      'oxxo': 'OXXO (Cash)',
      'mercadopago': 'Mercado Pago',
      'sepa': 'SEPA Transfer',
      'crypto': 'Cryptocurrency',
      'paypal': 'PayPal'
    };
    return labels[method] || method;
  };

  const getPaymentMethodIcon = (method: string) => {
    const icons: Record<string, string> = {
      'card': '💳',
      'ach': '🏦',
      'bank_transfer': '🏦',
      'oxxo': '🏪',
      'mercadopago': '🛒',
      'sepa': '🇪🇺',
      'crypto': '₿',
      'paypal': '💙'
    };
    return icons[method] || '💳';
  };

  const isLocationAllowed = () => {
    return location?.compliance_status === 'allowed';
  };

  const isLocationRestricted = () => {
    return location?.compliance_status === 'restricted';
  };

  const isLocationBlocked = () => {
    return location?.compliance_status === 'blocked';
  };

  const getCurrencySymbol = () => {
    const symbols: Record<string, string> = {
      'USD': '$',
      'MXN': '$',
      'EUR': '€',
      'GBP': '£',
      'CAD': 'C$'
    };
    return symbols[location?.currency || 'USD'] || '$';
  };

  return {
    location,
    compliance,
    isLoading,
    error,
    isLocationAllowed,
    isLocationRestricted,
    isLocationBlocked,
    getPaymentMethodLabel,
    getPaymentMethodIcon,
    getCurrencySymbol
  };
};
