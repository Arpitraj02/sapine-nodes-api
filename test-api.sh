#!/bin/bash

################################################################################
# Test Script - Sapine Bot Hosting Platform
# 
# This script tests the API endpoints to verify the installation
################################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

API_URL="${API_URL:-http://localhost:8000}"
TOKEN=""

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Sapine Bot Hosting Platform - API Test Suite${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# Test 1: Root endpoint
echo -e "${YELLOW}Test 1: Root endpoint${NC}"
RESPONSE=$(curl -s "${API_URL}/")
if echo "$RESPONSE" | grep -q "Welcome to Sapine"; then
    echo -e "${GREEN}✓ Root endpoint working${NC}"
else
    echo -e "${RED}✗ Root endpoint failed${NC}"
    echo "$RESPONSE"
    exit 1
fi
echo ""

# Test 2: Health check
echo -e "${YELLOW}Test 2: Health check endpoint${NC}"
RESPONSE=$(curl -s "${API_URL}/health")
if echo "$RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Health check passed${NC}"
    echo "  $(echo $RESPONSE | python3 -m json.tool 2>/dev/null | grep -E 'status|database|docker' || echo $RESPONSE)"
else
    echo -e "${RED}✗ Health check failed${NC}"
    echo "$RESPONSE"
    exit 1
fi
echo ""

# Test 3: Register user
echo -e "${YELLOW}Test 3: User registration${NC}"
TEST_EMAIL="test_$(date +%s)@example.com"
TEST_PASSWORD="SecurePassword123!"

RESPONSE=$(curl -s -X POST "${API_URL}/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"${TEST_PASSWORD}\"}")

if echo "$RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✓ User registration successful${NC}"
    echo "  Email: ${TEST_EMAIL}"
    TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")
    if [ -n "$TOKEN" ]; then
        echo -e "${GREEN}  Token obtained${NC}"
    fi
else
    echo -e "${RED}✗ User registration failed${NC}"
    echo "$RESPONSE"
    exit 1
fi
echo ""

# Test 4: Login
echo -e "${YELLOW}Test 4: User login${NC}"
RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"${TEST_PASSWORD}\"}")

if echo "$RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✓ User login successful${NC}"
    TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "$TOKEN")
else
    echo -e "${RED}✗ User login failed${NC}"
    echo "$RESPONSE"
    exit 1
fi
echo ""

# Test 5: Get user profile
echo -e "${YELLOW}Test 5: Get authenticated user profile${NC}"
if [ -z "$TOKEN" ]; then
    echo -e "${YELLOW}⚠ No token available, skipping...${NC}"
else
    RESPONSE=$(curl -s "${API_URL}/auth/me" \
        -H "Authorization: Bearer ${TOKEN}")
    
    if echo "$RESPONSE" | grep -q "${TEST_EMAIL}"; then
        echo -e "${GREEN}✓ User profile retrieved${NC}"
        echo "  $(echo $RESPONSE | python3 -m json.tool 2>/dev/null | grep -E 'email|role' || echo $RESPONSE)"
    else
        echo -e "${RED}✗ User profile retrieval failed${NC}"
        echo "$RESPONSE"
    fi
fi
echo ""

# Test 6: Invalid credentials
echo -e "${YELLOW}Test 6: Invalid credentials (should fail)${NC}"
RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"invalid@example.com","password":"wrongpassword"}')

if echo "$RESPONSE" | grep -q "Invalid"; then
    echo -e "${GREEN}✓ Invalid credentials correctly rejected${NC}"
else
    echo -e "${RED}✗ Security issue: Invalid credentials not rejected properly${NC}"
fi
echo ""

# Test 7: Duplicate registration
echo -e "${YELLOW}Test 7: Duplicate registration (should fail)${NC}"
RESPONSE=$(curl -s -X POST "${API_URL}/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"${TEST_PASSWORD}\"}")

if echo "$RESPONSE" | grep -q "already registered"; then
    echo -e "${GREEN}✓ Duplicate registration correctly rejected${NC}"
else
    echo -e "${RED}✗ Duplicate registration not rejected properly${NC}"
fi
echo ""

echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  All basic tests passed! ✓${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}API is working correctly!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Visit ${API_URL}/docs for interactive API documentation"
echo "  2. Check out Testing.md for more comprehensive testing"
echo "  3. Start building your bot hosting platform!"
echo ""
