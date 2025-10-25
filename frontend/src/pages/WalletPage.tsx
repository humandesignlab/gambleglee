import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { walletApi } from "@/services/api";
import { useLocation } from "@/hooks/useLocation";
import { DollarSign, CreditCard, ArrowUpDown, History, Plus, Minus, MapPin, AlertCircle } from "lucide-react";
import toast from "react-hot-toast";
import LoadingSpinner from "@/components/LoadingSpinner";

const WalletPage: React.FC = () => {
  const [depositAmount, setDepositAmount] = useState("");
  const [withdrawalAmount, setWithdrawalAmount] = useState("");
  const [showDepositModal, setShowDepositModal] = useState(false);
  const [showWithdrawalModal, setShowWithdrawalModal] = useState(false);
  
  const queryClient = useQueryClient();
  const { 
    location, 
    compliance, 
    isLoading: locationLoading, 
    isLocationAllowed, 
    isLocationBlocked,
    getPaymentMethodLabel,
    getPaymentMethodIcon,
    getCurrencySymbol
  } = useLocation();

  // Fetch wallet data
  const { data: wallet, isLoading: walletLoading } = useQuery({
    queryKey: ["wallet"],
    queryFn: walletApi.getWallet,
  });

  // Fetch transactions
  const { data: transactions, isLoading: transactionsLoading } = useQuery({
    queryKey: ["transactions"],
    queryFn: () => walletApi.getTransactions(1, 20),
  });

  // Deposit mutation
  const depositMutation = useMutation({
    mutationFn: walletApi.createDepositIntent,
    onSuccess: (data) => {
      toast.success("Deposit intent created successfully");
      setShowDepositModal(false);
      setDepositAmount("");
      // In a real app, you'd integrate with Stripe Elements here
      console.log("Stripe client secret:", data.client_secret);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to create deposit");
    },
  });

  // Withdrawal mutation
  const withdrawalMutation = useMutation({
    mutationFn: walletApi.requestWithdrawal,
    onSuccess: () => {
      toast.success("Withdrawal request submitted");
      setShowWithdrawalModal(false);
      setWithdrawalAmount("");
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to process withdrawal");
    },
  });

  const handleDeposit = () => {
    const amount = parseFloat(depositAmount);
    if (amount <= 0) {
      toast.error("Amount must be greater than 0");
      return;
    }
    if (amount > 10000) {
      toast.error("Maximum deposit amount is $10,000");
      return;
    }
    depositMutation.mutate(amount);
  };

  const handleWithdrawal = () => {
    const amount = parseFloat(withdrawalAmount);
    if (amount <= 0) {
      toast.error("Amount must be greater than 0");
      return;
    }
    if (amount > 5000) {
      toast.error("Maximum withdrawal amount is $5,000");
      return;
    }
    if (wallet && amount > wallet.balance) {
      toast.error("Insufficient balance");
      return;
    }
    withdrawalMutation.mutate(amount);
  };

  if (walletLoading || locationLoading) {
    return <LoadingSpinner className="flex justify-center py-8" />;
  }

  // Show location restriction message if blocked
  if (isLocationBlocked()) {
    return (
      <div className="space-y-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-center">
            <AlertCircle className="h-8 w-8 text-red-600 mr-4" />
            <div>
              <h2 className="text-lg font-semibold text-red-800">Access Restricted</h2>
              <p className="text-red-700 mt-1">
                GambleGlee is not available in your location ({location?.country_name}).
                We're working to expand to more regions soon.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Location Info */}
      {location && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center">
            <MapPin className="h-5 w-5 text-blue-600 mr-2" />
            <span className="text-sm text-blue-800">
              Detected location: {location.country_name} • 
              Payment processor: {location.payment_processor} • 
              Currency: {getCurrencySymbol()}{location.currency}
            </span>
          </div>
        </div>
      )}

      {/* Wallet Overview */}
      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Wallet</h1>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-green-50 rounded-lg p-4">
            <div className="flex items-center">
              <DollarSign className="h-8 w-8 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-green-600">Available Balance</p>
                <p className="text-2xl font-bold text-green-900">
                  ${wallet?.balance?.toFixed(2) || "0.00"}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-yellow-50 rounded-lg p-4">
            <div className="flex items-center">
              <ArrowUpDown className="h-8 w-8 text-yellow-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-yellow-600">Locked Balance</p>
                <p className="text-2xl font-bold text-yellow-900">
                  ${wallet?.locked_balance?.toFixed(2) || "0.00"}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-center">
              <CreditCard className="h-8 w-8 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-blue-600">Total Deposited</p>
                <p className="text-2xl font-bold text-blue-900">
                  ${wallet?.total_deposited?.toFixed(2) || "0.00"}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-4">
          <button
            onClick={() => setShowDepositModal(true)}
            className="btn-success flex items-center px-4 py-2"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Funds
          </button>
          
          <button
            onClick={() => setShowWithdrawalModal(true)}
            className="btn-outline flex items-center px-4 py-2"
          >
            <Minus className="h-4 w-4 mr-2" />
            Withdraw
          </button>
        </div>
      </div>

      {/* Transaction History */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <History className="h-5 w-5 mr-2" />
          Transaction History
        </h2>
        
        {transactionsLoading ? (
          <LoadingSpinner className="flex justify-center py-4" />
        ) : transactions?.items?.length ? (
          <div className="space-y-3">
            {transactions.items.map((transaction) => (
              <div
                key={transaction.id}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg"
              >
                <div className="flex items-center">
                  <div className={`w-3 h-3 rounded-full mr-3 ${
                    transaction.type === 'deposit' ? 'bg-green-500' :
                    transaction.type === 'withdrawal' ? 'bg-red-500' :
                    transaction.type === 'bet_won' ? 'bg-green-500' :
                    transaction.type === 'bet_lost' ? 'bg-red-500' :
                    'bg-gray-500'
                  }`} />
                  <div>
                    <p className="font-medium text-gray-900 capitalize">
                      {transaction.type.replace('_', ' ')}
                    </p>
                    <p className="text-sm text-gray-500">
                      {new Date(transaction.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`font-semibold ${
                    transaction.type === 'deposit' || transaction.type === 'bet_won' 
                      ? 'text-green-600' 
                      : 'text-red-600'
                  }`}>
                    {transaction.type === 'deposit' || transaction.type === 'bet_won' ? '+' : '-'}
                    ${transaction.amount.toFixed(2)}
                  </p>
                  <p className="text-sm text-gray-500 capitalize">
                    {transaction.status}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-500">No transactions yet</p>
            <p className="text-sm text-gray-400 mt-1">
              Start by adding funds to your wallet
            </p>
          </div>
        )}
      </div>

      {/* Deposit Modal */}
      {showDepositModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Funds</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Amount
                </label>
                <input
                  type="number"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  className="input w-full"
                  placeholder="Enter amount"
                  min="1"
                  max={compliance?.deposit_limits?.daily || 10000}
                  step="0.01"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Maximum: {getCurrencySymbol()}{compliance?.deposit_limits?.daily || 10000} daily
                </p>
              </div>
              
              {/* Payment Methods */}
              {location?.payment_methods && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Payment Methods Available
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {location.payment_methods.map((method) => (
                      <div key={method} className="flex items-center p-2 border border-gray-200 rounded-lg">
                        <span className="text-lg mr-2">{getPaymentMethodIcon(method)}</span>
                        <span className="text-sm text-gray-700">{getPaymentMethodLabel(method)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="flex space-x-3">
                <button
                  onClick={() => setShowDepositModal(false)}
                  className="btn-outline flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeposit}
                  disabled={depositMutation.isPending || !isLocationAllowed()}
                  className="btn-success flex-1"
                >
                  {depositMutation.isPending ? (
                    <LoadingSpinner size="sm" />
                  ) : (
                    "Continue to Payment"
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Withdrawal Modal */}
      {showWithdrawalModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Withdraw Funds</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Amount
                </label>
                <input
                  type="number"
                  value={withdrawalAmount}
                  onChange={(e) => setWithdrawalAmount(e.target.value)}
                  className="input w-full"
                  placeholder="Enter amount"
                  min="1"
                  max="5000"
                  step="0.01"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Available: ${wallet?.balance?.toFixed(2) || "0.00"} | Maximum: $5,000
                </p>
              </div>
              
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <p className="text-sm text-yellow-800">
                  <strong>Note:</strong> Withdrawals are processed manually and may take 3-5 business days.
                </p>
              </div>
              
              <div className="flex space-x-3">
                <button
                  onClick={() => setShowWithdrawalModal(false)}
                  className="btn-outline flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={handleWithdrawal}
                  disabled={withdrawalMutation.isPending}
                  className="btn-primary flex-1"
                >
                  {withdrawalMutation.isPending ? (
                    <LoadingSpinner size="sm" />
                  ) : (
                    "Request Withdrawal"
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WalletPage;
