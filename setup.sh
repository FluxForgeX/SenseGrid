#!/bin/bash

# SenseGrid Setup Script
# Works on: Linux, macOS, Raspberry Pi OS (Debian-based)

set -e

echo "========================================="
echo "  SenseGrid Setup Script"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si)
        VER=$(lsb_release -sr)
    else
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    echo -e "${GREEN}Detected OS: $OS $VER${NC}"
}

# Check Python version
check_python() {
    echo -e "\n${YELLOW}Checking Python...${NC}"
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
        
        # Check if version is 3.9+
        MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        if [[ $MAJOR -ge 3 && $MINOR -ge 9 ]]; then
            echo -e "${GREEN}✓ Python version is compatible${NC}"
        else
            echo -e "${RED}✗ Python 3.9+ required. Found $PYTHON_VERSION${NC}"
            echo "  Install with: sudo apt install python3.11 python3.11-venv"
            exit 1
        fi
    else
        echo -e "${RED}✗ Python3 not found${NC}"
        echo "  Install with: sudo apt install python3 python3-venv python3-pip"
        exit 1
    fi
}

# Check Node.js
check_node() {
    echo -e "\n${YELLOW}Checking Node.js...${NC}"
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo -e "${GREEN}✓ Node.js $NODE_VERSION found${NC}"
    else
        echo -e "${RED}✗ Node.js not found${NC}"
        echo "  Install with: curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt install -y nodejs"
        exit 1
    fi
    
    if command -v npm &> /dev/null; then
        NPM_VERSION=$(npm --version)
        echo -e "${GREEN}✓ npm $NPM_VERSION found${NC}"
    else
        echo -e "${RED}✗ npm not found${NC}"
        exit 1
    fi
}

# Setup Backend
setup_backend() {
    echo -e "\n${YELLOW}Setting up Backend...${NC}"
    cd backend
    
    # Create virtual environment if not exists
    if [[ ! -d ".venv" ]]; then
        echo "Creating Python virtual environment..."
        python3 -m venv .venv
    fi
    
    # Activate venv
    source .venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Create .env if not exists
    if [[ ! -f ".env" ]]; then
        echo "Creating .env from template..."
        cp .env.example .env
        
        # Generate random JWT secret
        JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/your-super-secret-jwt-key-change-in-production-min-32-chars/$JWT_SECRET/" .env
        else
            # Linux/Raspberry Pi
            sed -i "s/your-super-secret-jwt-key-change-in-production-min-32-chars/$JWT_SECRET/" .env
        fi
        echo -e "${GREEN}✓ Generated secure JWT secret${NC}"
        
        # On Raspberry Pi, add local IP to CORS origins
        LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [[ -n "$LOCAL_IP" && "$LOCAL_IP" != "127.0.0.1" ]]; then
            echo -e "${YELLOW}Adding local IP ($LOCAL_IP) to CORS origins...${NC}"
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|CORS_ORIGINS=|CORS_ORIGINS=http://$LOCAL_IP:5173,http://$LOCAL_IP:5174,|" .env
            else
                sed -i "s|CORS_ORIGINS=|CORS_ORIGINS=http://$LOCAL_IP:5173,http://$LOCAL_IP:5174,|" .env
            fi
        fi
    else
        echo -e "${YELLOW}⚠ .env already exists, skipping${NC}"
    fi
    
    # Test database
    echo "Testing database connection..."
    python3 -c "from database import init_db; init_db(); print('✓ Database initialized')"
    
    cd ..
    echo -e "${GREEN}✓ Backend setup complete${NC}"
}

# Setup Frontend
setup_frontend() {
    echo -e "\n${YELLOW}Setting up Frontend...${NC}"
    cd frontend
    
    # Install npm dependencies
    echo "Installing npm dependencies..."
    npm install
    
    # Verify critical packages are installed
    echo "Verifying required packages..."
    if ! npm list react-router-dom &>/dev/null || ! npm list framer-motion &>/dev/null; then
        echo "Installing missing packages..."
        npm install react-router-dom framer-motion
    fi
    
    # Create .env if not exists
    if [[ ! -f ".env" ]]; then
        echo "Creating .env from template..."
        cp .env.example .env
        
        # On Raspberry Pi, update .env with local IP for network access
        LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [[ -n "$LOCAL_IP" && "$LOCAL_IP" != "127.0.0.1" ]]; then
            echo -e "${YELLOW}Configuring for network access (IP: $LOCAL_IP)...${NC}"
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|VITE_API_URL=http://localhost:8000/api|VITE_API_URL=http://$LOCAL_IP:8000/api|" .env
                sed -i '' "s|VITE_WS_URL=http://localhost:8000|VITE_WS_URL=http://$LOCAL_IP:8000|" .env
            else
                sed -i "s|VITE_API_URL=http://localhost:8000/api|VITE_API_URL=http://$LOCAL_IP:8000/api|" .env
                sed -i "s|VITE_WS_URL=http://localhost:8000|VITE_WS_URL=http://$LOCAL_IP:8000|" .env
            fi
        fi
    else
        echo -e "${YELLOW}⚠ .env already exists, skipping${NC}"
    fi
    
    cd ..
    echo -e "${GREEN}✓ Frontend setup complete${NC}"
}

# Get local IP for Raspberry Pi
get_local_ip() {
    if command -v hostname &> /dev/null; then
        LOCAL_IP=$(hostname -I | awk '{print $1}')
    else
        LOCAL_IP="localhost"
    fi
    echo $LOCAL_IP
}

# Print run instructions
print_instructions() {
    LOCAL_IP=$(get_local_ip)
    
    echo -e "\n${GREEN}=========================================${NC}"
    echo -e "${GREEN}  Setup Complete!${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo -e "${YELLOW}To start the application:${NC}"
    echo ""
    echo "  Terminal 1 (Backend):"
    echo "    cd backend"
    echo "    source .venv/bin/activate"
    echo "    python -m uvicorn main:app --host 0.0.0.0 --port 8000"
    echo ""
    echo "  Terminal 2 (Frontend):"
    echo "    cd frontend"
    echo "    npm run dev -- --host"
    echo ""
    echo -e "${YELLOW}Access the app:${NC}"
    echo "  Local:   http://localhost:5173"
    echo "  Network: http://$LOCAL_IP:5173"
    echo ""
    echo -e "${YELLOW}API Documentation:${NC}"
    echo "  http://localhost:8000/docs"
    echo ""
    echo -e "${YELLOW}For Raspberry Pi (run on boot):${NC}"
    echo "  See: docs/raspberry-pi-setup.md"
    echo ""
}

# Main execution
main() {
    detect_os
    check_python
    check_node
    setup_backend
    setup_frontend
    print_instructions
}

main "$@"
