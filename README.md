# GambleGlee - Social Betting Platform

A social betting platform that combines the excitement of betting with the fun and engagement of a social network.

## 🎯 Overview

GambleGlee is a peer-to-peer social betting platform where friends can bet against each other on various outcomes, from casual predictions to live trick shot events. The platform emphasizes responsible gambling, social interaction, and secure financial transactions.

## 🏗️ Architecture

- **Frontend**: React 18+ with TypeScript, Vite, TailwindCSS
- **Backend**: FastAPI (Python 3.11+) with async/await
- **Database**: PostgreSQL 15+ with Redis for caching
- **Live Streaming**: AWS IVS (Interactive Video Service)
- **Payments**: Stripe Connect for peer-to-peer transactions
- **Infrastructure**: AWS (EC2, RDS, ElastiCache, S3, CloudFront)

## 📁 Project Structure

```
/gambleglee
  /frontend          # React application
  /backend           # FastAPI application
  /infrastructure    # IaC (Terraform/CloudFormation)
  /docs              # Technical documentation
  /scripts           # Deployment and utility scripts
  docker-compose.yml # Development environment
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker (recommended)

### Development Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd gambleglee
   ```

2. **Run the setup script**

   ```bash
   ./scripts/setup-dev.sh
   ```

3. **Start the development servers**

   ```bash
   # Backend (Terminal 1)
   cd backend
   uvicorn app.main:app --reload

   # Frontend (Terminal 2)
   cd frontend
   npm run dev
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## ✨ Features

### MVP (Phase 1) - Current Implementation

- ✅ User registration and authentication
- ✅ JWT-based session management
- ✅ Responsive React frontend
- ✅ Basic user profiles and social features
- 🔄 Basic KYC (age verification) - In Progress
- 🔄 Peer-to-peer betting with escrow - In Progress
- 🔄 Live trick shot betting with AWS IVS - In Progress

### Enhanced Features (Phase 2)

- Advanced betting types (time-based, multi-outcome)
- Full KYC/AML compliance with Persona/Onfido
- Gamification elements (badges, leaderboards)
- Mobile application (React Native)
- Real-time notifications

### Scale Features (Phase 3)

- AI/ML fraud detection
- Advanced analytics and insights
- Content creation tools
- Premium features and subscriptions

## 🔒 Compliance & Security

- **US Gambling Regulations**: Geolocation verification, state-by-state compliance
- **KYC/AML**: Identity verification, transaction monitoring
- **Responsible Gambling**: Deposit limits, self-exclusion, session limits
- **Data Protection**: GDPR-ready, encryption at rest and in transit
- **Financial Security**: PCI DSS compliance via Stripe, escrow protection

## 🛠️ Technology Stack

### Backend

- **FastAPI**: High-performance Python web framework
- **SQLAlchemy 2.0**: Async ORM with PostgreSQL
- **Redis**: Caching and session management
- **Celery**: Background task processing
- **Socket.IO**: Real-time WebSocket communication

### Frontend

- **React 18**: Modern React with hooks
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool and dev server
- **TailwindCSS**: Utility-first CSS framework
- **React Query**: Server state management
- **Zustand**: Client state management

### Infrastructure

- **AWS**: Cloud hosting and services
- **Docker**: Containerization
- **PostgreSQL**: Primary database
- **Redis**: Caching and pub/sub
- **AWS IVS**: Live streaming infrastructure

## 📊 Database Schema

### Core Tables

- `users`: User accounts and profiles
- `wallets`: User balances and financial data
- `transactions`: All financial transactions
- `bets`: Betting events and outcomes
- `bet_participants`: User participation in bets
- `friendships`: Social connections
- `notifications`: User notifications
- `trick_shot_events`: Live streaming events

## 🔧 Development

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
cd backend
alembic upgrade head
```

### Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 🚀 Deployment

### Environment Variables

Copy the example environment files and configure:

- `backend/env.example` → `backend/.env`
- `frontend/env.example` → `frontend/.env`

### Production Deployment

1. Set up AWS infrastructure (RDS, ElastiCache, EC2)
2. Configure environment variables
3. Run database migrations
4. Deploy backend and frontend
5. Set up monitoring and logging

## 📈 Roadmap

### Phase 1: MVP (Months 1-3)

- [x] Project structure and authentication
- [ ] Wallet system with Stripe integration
- [ ] Basic betting functionality
- [ ] Social features (friends, leaderboards)
- [ ] Live streaming integration

### Phase 2: Enhanced Features (Months 4-6)

- [ ] Advanced betting types
- [ ] Full KYC/AML compliance
- [ ] Mobile application
- [ ] Real-time notifications
- [ ] Gamification elements

### Phase 3: Scale & Advanced (Months 7-12)

- [ ] AI/ML fraud detection
- [ ] Advanced analytics
- [ ] Content creation tools
- [ ] Premium features
- [ ] Multi-region deployment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

Proprietary - GambleGlee Inc. All rights reserved.

## 🆘 Support

For technical support or questions:

- Email: support@gambleglee.com
- Documentation: [Internal Wiki]
- Issues: [GitHub Issues]

---

**⚠️ Important**: This platform is for users 18+ only. Please gamble responsibly.
