// User types
export interface User {
  id: number;
  email: string;
  username: string;
  first_name?: string;
  last_name?: string;
  kyc_status: "pending" | "verified" | "rejected" | "expired";
  status: "active" | "suspended" | "banned" | "self_excluded";
  is_email_verified: boolean;
  created_at: string;
}

// Auth types
export interface LoginRequest {
  email_or_username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  first_name?: string;
  last_name?: string;
  date_of_birth?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// Wallet types
export interface Wallet {
  id: number;
  user_id: number;
  balance: number;
  locked_balance: number;
  total_deposited: number;
  total_withdrawn: number;
  total_wagered: number;
  total_won: number;
  created_at: string;
  updated_at: string;
}

export interface Transaction {
  id: number;
  user_id: number;
  wallet_id: number;
  type:
    | "deposit"
    | "withdrawal"
    | "bet_placed"
    | "bet_won"
    | "bet_lost"
    | "refund"
    | "fee";
  amount: number;
  status: "pending" | "completed" | "failed" | "cancelled";
  description?: string;
  created_at: string;
  completed_at?: string;
}

// Betting types
export interface Bet {
  id: number;
  creator_id: number;
  type: "binary" | "time_based" | "multi_outcome" | "trick_shot";
  title: string;
  description?: string;
  amount: number;
  max_participants?: number;
  min_participants: number;
  is_public: boolean;
  status: "pending" | "active" | "locked" | "resolved" | "cancelled";
  outcome: "pending" | "win" | "lose" | "push";
  resolution_notes?: string;
  trick_shot_event_id?: number;
  time_limit_seconds?: number;
  created_at: string;
  updated_at: string;
  locked_at?: string;
  resolved_at?: string;
  creator: User;
  participants: BetParticipant[];
}

export interface BetParticipant {
  id: number;
  bet_id: number;
  user_id: number;
  position: string;
  amount: number;
  payout: number;
  outcome: "pending" | "win" | "lose" | "push";
  joined_at: string;
  user: User;
}

// Social types
export interface Friendship {
  id: number;
  user_id: number;
  friend_id: number;
  status: "pending" | "accepted" | "blocked";
  created_at: string;
  updated_at: string;
  user: User;
  friend: User;
}

export interface Notification {
  id: number;
  user_id: number;
  type:
    | "bet_invitation"
    | "bet_resolved"
    | "friend_request"
    | "friend_accepted"
    | "trick_shot_event"
    | "balance_update";
  title: string;
  message: string;
  is_read: boolean;
  bet_id?: number;
  friend_id?: number;
  trick_shot_event_id?: number;
  created_at: string;
  read_at?: string;
}

// Event types
export interface TrickShotEvent {
  id: number;
  title: string;
  description?: string;
  stream_url?: string;
  stream_key?: string;
  aws_ivs_channel_arn?: string;
  status: "scheduled" | "live" | "ended";
  scheduled_at: string;
  started_at?: string;
  ended_at?: string;
  created_at: string;
  bets: Bet[];
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Form types
export interface LoginForm {
  email_or_username: string;
  password: string;
}

export interface RegisterForm {
  email: string;
  username: string;
  password: string;
  confirmPassword: string;
  first_name?: string;
  last_name?: string;
  date_of_birth?: string;
}

export interface CreateBetForm {
  type: "binary" | "time_based" | "multi_outcome" | "trick_shot";
  title: string;
  description?: string;
  amount: number;
  max_participants?: number;
  is_public: boolean;
  time_limit_seconds?: number;
  trick_shot_event_id?: number;
}
