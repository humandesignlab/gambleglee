#!/bin/bash
# GambleGlee Development Environment Setup Script

set -e

echo "🚀 Setting up GambleGlee development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    print_status "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Check if Node.js is installed
check_node() {
    print_status "Checking Node.js installation..."
    if ! command -v node &> /dev/null; then
        print_warning "Node.js is not installed. Installing via nvm..."
        if ! command -v nvm &> /dev/null; then
            print_error "nvm is not installed. Please install nvm first."
            echo "Visit: https://github.com/nvm-sh/nvm"
            exit 1
        fi
        nvm install 18
        nvm use 18
    fi
    
    print_success "Node.js is installed"
}

# Check if Python is installed
check_python() {
    print_status "Checking Python installation..."
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.11+ first."
        exit 1
    fi
    
    # Check Python version
    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [[ $(echo "$python_version 3.11" | awk '{print ($1 >= $2)}') == 0 ]]; then
        print_error "Python 3.11+ is required. Current version: $python_version"
        exit 1
    fi
    
    print_success "Python $python_version is installed"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    mkdir -p nginx/ssl
    mkdir -p monitoring/grafana/dashboards
    mkdir -p monitoring/grafana/datasources
    mkdir -p logs
    print_success "Directories created"
}

# Set up environment variables
setup_env() {
    print_status "Setting up environment variables..."
    
    # Backend environment
    if [ ! -f backend/.env ]; then
        cat > backend/.env << EOF
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/gambleglee
REDIS_URL=redis://localhost:6379

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# Email (for testing)
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_TLS=false

# Storage
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=gambleglee

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
EOF
        print_success "Backend environment file created"
    else
        print_warning "Backend environment file already exists"
    fi
    
    # Frontend environment
    if [ ! -f frontend/.env ]; then
        cat > frontend/.env << EOF
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_ENVIRONMENT=development
EOF
        print_success "Frontend environment file created"
    else
        print_warning "Frontend environment file already exists"
    fi
}

# Install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    cd backend
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-test.txt
    cd ..
    print_success "Python dependencies installed"
}

# Install Node.js dependencies
install_node_deps() {
    print_status "Installing Node.js dependencies..."
    cd frontend
    npm install
    cd ..
    print_success "Node.js dependencies installed"
}

# Start development services
start_services() {
    print_status "Starting development services..."
    docker-compose up -d postgres redis mailhog minio prometheus grafana
    print_success "Development services started"
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Services are running"
    else
        print_error "Some services failed to start"
        docker-compose ps
        exit 1
    fi
}

# Run database migrations
run_migrations() {
    print_status "Running database migrations..."
    cd backend
    source venv/bin/activate
    alembic upgrade head
    cd ..
    print_success "Database migrations completed"
}

# Run tests
run_tests() {
    print_status "Running tests..."
    cd backend
    source venv/bin/activate
    pytest tests/unit/ -v
    cd ..
    print_success "Tests completed"
}

# Display service URLs
show_urls() {
    print_success "🎉 GambleGlee development environment is ready!"
    echo ""
    echo "📊 Service URLs:"
    echo "  Frontend:     http://localhost:3000"
    echo "  Backend API:  http://localhost:8000"
    echo "  API Docs:     http://localhost:8000/docs"
    echo "  Mailhog:      http://localhost:8025"
    echo "  MinIO:        http://localhost:9001"
    echo "  Prometheus:   http://localhost:9090"
    echo "  Grafana:      http://localhost:3001"
    echo ""
    echo "🔧 Development Commands:"
    echo "  Start all services:    docker-compose up -d"
    echo "  Stop all services:     docker-compose down"
    echo "  View logs:             docker-compose logs -f"
    echo "  Run tests:             pytest"
    echo "  Run backend:           cd backend && uvicorn app.main:app --reload"
    echo "  Run frontend:          cd frontend && npm run dev"
    echo ""
    echo "📝 Next Steps:"
    echo "  1. Start the backend:  cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
    echo "  2. Start the frontend: cd frontend && npm run dev"
    echo "  3. Visit http://localhost:3000 to see the app"
    echo ""
}

# Main execution
main() {
    print_status "Starting GambleGlee development environment setup..."
    
    check_docker
    check_node
    check_python
    create_directories
    setup_env
    install_python_deps
    install_node_deps
    start_services
    run_migrations
    run_tests
    show_urls
    
    print_success "🎉 Setup completed successfully!"
}

# Run main function
main "$@"
