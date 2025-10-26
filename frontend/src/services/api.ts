import axios, { AxiosInstance, AxiosResponse } from "axios";
import { useAuthStore } from "@/store/authStore";
import {
  AuthResponse,
  User,
  LoginRequest,
  RegisterRequest,
  Wallet,
  Transaction,
  Bet,
  Friendship,
  Notification,
  TrickShotEvent,
} from "@/types";

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: "/api/v1",
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = useAuthStore.getState().refreshToken;
        if (refreshToken) {
          const response = await api.post("/auth/refresh", {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token } = response.data;
          useAuthStore
            .getState()
            .setAuth(useAuthStore.getState().user!, {
              access_token,
              refresh_token,
              token_type: "bearer",
              expires_in: 3600,
              user: useAuthStore.getState().user!,
            });

          // Retry original request
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        useAuthStore.getState().logout();
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const formData = new FormData();
    formData.append("username", data.email_or_username);
    formData.append("password", data.password);

    const response: AxiosResponse<AuthResponse> = await api.post(
      "/auth/login",
      formData,
      {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      }
    );
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<User> => {
    const response: AxiosResponse<User> = await api.post(
      "/auth/register",
      data
    );
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response: AxiosResponse<User> = await api.get("/auth/me");
    return response.data;
  },

  logout: async (): Promise<void> => {
    await api.post("/auth/logout");
  },
};

// User API
export const userApi = {
  getProfile: async (): Promise<User> => {
    const response: AxiosResponse<User> = await api.get("/users/profile");
    return response.data;
  },

  updateProfile: async (data: Partial<User>): Promise<User> => {
    const response: AxiosResponse<User> = await api.put("/users/profile", data);
    return response.data;
  },
};

// Wallet API
export const walletApi = {
  getWallet: async (): Promise<Wallet> => {
    const response: AxiosResponse<Wallet> = await api.get("/wallet");
    return response.data;
  },

  getTransactions: async (
    page = 1,
    limit = 20
  ): Promise<{ items: Transaction[]; total: number }> => {
    const response: AxiosResponse<{ items: Transaction[]; total: number }> =
      await api.get(`/wallet/transactions?page=${page}&limit=${limit}`);
    return response.data;
  },

  createDepositIntent: async (
    amount: number
  ): Promise<{ client_secret: string }> => {
    const response: AxiosResponse<{ client_secret: string }> = await api.post(
      "/wallet/deposit",
      { amount }
    );
    return response.data;
  },

  requestWithdrawal: async (amount: number): Promise<void> => {
    await api.post("/wallet/withdraw", { amount });
  },
};

// Bets API
export const betsApi = {
  getBets: async (
    page = 1,
    limit = 20
  ): Promise<{ items: Bet[]; total: number }> => {
    const response: AxiosResponse<{ items: Bet[]; total: number }> =
      await api.get(`/bets?page=${page}&limit=${limit}`);
    return response.data;
  },

  getBet: async (id: number): Promise<Bet> => {
    const response: AxiosResponse<Bet> = await api.get(`/bets/${id}`);
    return response.data;
  },

  createBet: async (data: any): Promise<Bet> => {
    const response: AxiosResponse<Bet> = await api.post("/bets", data);
    return response.data;
  },

  joinBet: async (id: number, position: string): Promise<void> => {
    await api.post(`/bets/${id}/join`, { position });
  },

  resolveBet: async (
    id: number,
    outcome: string,
    notes?: string
  ): Promise<void> => {
    await api.post(`/bets/${id}/resolve`, { outcome, notes });
  },
};

// Friends API
export const friendsApi = {
  getFriends: async (): Promise<Friendship[]> => {
    const response: AxiosResponse<Friendship[]> = await api.get("/friends");
    return response.data;
  },

  searchUsers: async (query: string): Promise<User[]> => {
    const response: AxiosResponse<User[]> = await api.get(
      `/friends/search?q=${query}`
    );
    return response.data;
  },

  sendFriendRequest: async (userId: number): Promise<void> => {
    await api.post(`/friends/request`, { user_id: userId });
  },

  acceptFriendRequest: async (friendshipId: number): Promise<void> => {
    await api.post(`/friends/${friendshipId}/accept`);
  },

  removeFriend: async (friendshipId: number): Promise<void> => {
    await api.delete(`/friends/${friendshipId}`);
  },
};

// Events API
export const eventsApi = {
  getEvents: async (): Promise<TrickShotEvent[]> => {
    const response: AxiosResponse<TrickShotEvent[]> = await api.get("/events");
    return response.data;
  },

  getEvent: async (id: number): Promise<TrickShotEvent> => {
    const response: AxiosResponse<TrickShotEvent> = await api.get(
      `/events/${id}`
    );
    return response.data;
  },
};

// Notifications API
export const notificationsApi = {
  getNotifications: async (): Promise<Notification[]> => {
    const response: AxiosResponse<Notification[]> = await api.get(
      "/notifications"
    );
    return response.data;
  },

  markAsRead: async (id: number): Promise<void> => {
    await api.post(`/notifications/${id}/read`);
  },

  markAllAsRead: async (): Promise<void> => {
    await api.post("/notifications/read-all");
  },
};

export default api;
