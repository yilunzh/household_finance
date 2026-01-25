#!/bin/bash
# Smart iOS test runner with auto-detection and auto-recovery
# Usage: ./scripts/ios-test.sh [--test <name>] [--all] [--rebuild] [--verbose]

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IOS_DIR="$PROJECT_ROOT/ios/HouseholdTracker"
MAESTRO_DIR="$IOS_DIR/maestro"
BACKEND_PORT=5001
BUNDLE_ID="com.householdtracker.app"
DEFAULT_SIMULATOR="iPhone 16"
MAESTRO_BIN="$HOME/.maestro/bin/maestro"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
VERBOSE=false
REBUILD=false
RUN_ALL=false
SPECIFIC_TEST=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --test)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        --all)
            RUN_ALL=true
            shift
            ;;
        --rebuild)
            REBUILD=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--test <name>] [--all] [--rebuild] [--verbose]"
            echo ""
            echo "Options:"
            echo "  --test <name>  Run specific test (e.g., --test login-flow)"
            echo "  --all          Run all tests"
            echo "  --rebuild      Force rebuild even if app installed"
            echo "  --verbose      Show detailed progress"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging functions
log() {
    echo -e "${BLUE}[ios-test]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[ios-test]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[ios-test]${NC} $1"
}

log_error() {
    echo -e "${RED}[ios-test]${NC} $1"
}

verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[ios-test]${NC} $1"
    fi
}

# ============================================================================
# Environment Detection and Auto-Fix Functions
# ============================================================================

check_backend() {
    if lsof -i :$BACKEND_PORT -sTCP:LISTEN > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

start_backend() {
    log "Starting backend server..."
    cd "$PROJECT_ROOT"

    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    # Start backend in background
    NO_RELOAD=1 python app.py > /tmp/ios-test-backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/ios-test-backend.pid

    # Wait for backend to be ready
    log "Waiting for backend to start..."
    for i in {1..30}; do
        if curl -s http://localhost:$BACKEND_PORT/api/v1/config > /dev/null 2>&1; then
            log_success "Backend started (PID: $BACKEND_PID)"
            return 0
        fi
        sleep 1
    done

    log_error "Backend failed to start. Check /tmp/ios-test-backend.log"
    return 1
}

check_test_data() {
    # Try to login with demo credentials
    RESPONSE=$(curl -s -X POST http://localhost:$BACKEND_PORT/api/v1/auth/login \
        -H "Content-Type: application/json" \
        -d '{"email":"demo_alice@example.com","password":"password123"}' \
        2>/dev/null)

    if echo "$RESPONSE" | grep -q "access_token"; then
        return 0
    else
        return 1
    fi
}

seed_test_data() {
    log "Seeding test data..."
    cd "$PROJECT_ROOT"

    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    if python seed_test_users.py; then
        log_success "Test data seeded"
        return 0
    else
        log_error "Failed to seed test data"
        return 1
    fi
}

setup_java() {
    # Check if JAVA_HOME is already set and valid
    if [ -n "$JAVA_HOME" ] && [ -x "$JAVA_HOME/bin/java" ]; then
        verbose "Java found at $JAVA_HOME"
        return 0
    fi

    # Common Java installation paths on macOS
    JAVA_PATHS=(
        "/usr/local/opt/openjdk@17"
        "/opt/homebrew/opt/openjdk@17"
        "/usr/local/opt/openjdk"
        "/opt/homebrew/opt/openjdk"
        "/Library/Java/JavaVirtualMachines/openjdk-17.jdk/Contents/Home"
    )

    for JAVA_PATH in "${JAVA_PATHS[@]}"; do
        if [ -d "$JAVA_PATH" ] && [ -x "$JAVA_PATH/bin/java" ]; then
            export JAVA_HOME="$JAVA_PATH"
            export PATH="$JAVA_HOME/bin:$PATH"
            verbose "Java found at $JAVA_PATH"
            return 0
        fi
    done

    log_error "Java not found. Install with: brew install openjdk@17"
    return 1
}

check_maestro() {
    if [ -x "$MAESTRO_BIN" ]; then
        return 0
    else
        return 1
    fi
}

install_maestro() {
    log "Installing Maestro..."
    curl -Ls "https://get.maestro.mobile.dev" | bash

    if [ -x "$MAESTRO_BIN" ]; then
        log_success "Maestro installed"
        return 0
    else
        log_error "Maestro installation failed"
        return 1
    fi
}

get_booted_simulator() {
    xcrun simctl list devices | grep "Booted" | head -1 | sed 's/.*(\([^)]*\)).*/\1/'
}

check_simulator() {
    BOOTED=$(get_booted_simulator)
    if [ -n "$BOOTED" ]; then
        verbose "Simulator booted: $BOOTED"
        return 0
    else
        return 1
    fi
}

boot_simulator() {
    log "Booting simulator: $DEFAULT_SIMULATOR..."

    # Get the UDID for the default simulator
    UDID=$(xcrun simctl list devices available | grep "$DEFAULT_SIMULATOR" | grep -v "unavailable" | head -1 | sed 's/.*(\([^)]*\)).*/\1/')

    if [ -z "$UDID" ]; then
        log_warn "iPhone 16 not found, trying to find any available iPhone..."
        UDID=$(xcrun simctl list devices available | grep "iPhone" | grep -v "unavailable" | head -1 | sed 's/.*(\([^)]*\)).*/\1/')
    fi

    if [ -z "$UDID" ]; then
        log_error "No iPhone simulator found"
        return 1
    fi

    xcrun simctl boot "$UDID" 2>/dev/null || true

    # Wait for simulator to boot
    for i in {1..30}; do
        if check_simulator; then
            log_success "Simulator booted"
            return 0
        fi
        sleep 1
    done

    log_error "Simulator failed to boot"
    return 1
}

check_app_installed() {
    BOOTED=$(get_booted_simulator)
    if [ -z "$BOOTED" ]; then
        return 1
    fi

    # Check if app is installed
    if xcrun simctl listapps "$BOOTED" 2>/dev/null | grep -q "$BUNDLE_ID"; then
        verbose "App installed on simulator"
        return 0
    else
        return 1
    fi
}

build_and_install() {
    log "Building and installing app..."
    cd "$IOS_DIR"

    # Generate Xcode project if needed
    if [ ! -f "HouseholdTracker.xcodeproj/project.pbxproj" ] || [ "project.yml" -nt "HouseholdTracker.xcodeproj/project.pbxproj" ]; then
        log "Generating Xcode project..."
        if command -v xcodegen &> /dev/null; then
            xcodegen generate
        else
            log_error "xcodegen not found. Install with: brew install xcodegen"
            return 1
        fi
    fi

    BOOTED=$(get_booted_simulator)
    if [ -z "$BOOTED" ]; then
        log_error "No simulator booted"
        return 1
    fi

    # Build for simulator
    log "Building app for simulator..."
    xcodebuild \
        -project HouseholdTracker.xcodeproj \
        -scheme HouseholdTracker \
        -destination "id=$BOOTED" \
        -configuration Debug \
        build \
        2>&1 | if [ "$VERBOSE" = true ]; then cat; else grep -E "(error:|warning:|BUILD|Compiling)" || true; fi

    BUILD_RESULT=${PIPESTATUS[0]}
    if [ $BUILD_RESULT -ne 0 ]; then
        log_error "Build failed"
        return 1
    fi

    # Find and install the app
    APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData -name "HouseholdTracker.app" -path "*Debug-iphonesimulator*" -type d 2>/dev/null | head -1)

    if [ -z "$APP_PATH" ]; then
        log_error "Could not find built app"
        return 1
    fi

    log "Installing app to simulator..."
    xcrun simctl install "$BOOTED" "$APP_PATH"

    log_success "App installed"
    return 0
}

run_maestro_tests() {
    log "Running Maestro tests..."
    cd "$MAESTRO_DIR"

    # Create results directory
    RESULTS_DIR="/tmp/ios-test-results-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$RESULTS_DIR"

    # Determine which tests to run
    if [ -n "$SPECIFIC_TEST" ]; then
        TEST_PATH="$SPECIFIC_TEST"
        if [[ ! "$TEST_PATH" == *.yaml ]]; then
            TEST_PATH="${TEST_PATH}.yaml"
        fi
        if [ ! -f "$TEST_PATH" ]; then
            log_error "Test not found: $TEST_PATH"
            return 1
        fi
        log "Running test: $TEST_PATH"
    elif [ "$RUN_ALL" = true ]; then
        TEST_PATH="."
        log "Running all tests"
    else
        # Default to login flow as smoke test
        TEST_PATH="login-flow.yaml"
        log "Running smoke test: $TEST_PATH"
    fi

    # Run Maestro tests
    "$MAESTRO_BIN" test "$TEST_PATH" --format junit --output "$RESULTS_DIR/results.xml" 2>&1 | tee "$RESULTS_DIR/output.log"
    TEST_EXIT_CODE=${PIPESTATUS[0]}

    # Output results summary
    echo ""
    echo "=============================================="
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        log_success "All tests passed!"
        echo "Results: $RESULTS_DIR"

        # Create verification marker
        touch "$PROJECT_ROOT/.ios-verified"
        log_success "Created .ios-verified marker"
    else
        log_error "Tests failed (exit code: $TEST_EXIT_CODE)"
        echo "Results: $RESULTS_DIR"
        echo ""
        echo "Failure details:"
        echo "  - Log: $RESULTS_DIR/output.log"
        echo "  - Screenshots: ~/.maestro/tests/*/screenshot-*.png"

        # Find latest test directory with screenshots
        LATEST_TEST_DIR=$(ls -td ~/.maestro/tests/*/ 2>/dev/null | head -1)
        if [ -n "$LATEST_TEST_DIR" ]; then
            echo "  - Latest run: $LATEST_TEST_DIR"
            ls "$LATEST_TEST_DIR"screenshot-*.png 2>/dev/null | head -5 || true
        fi
    fi
    echo "=============================================="

    return $TEST_EXIT_CODE
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log "Starting iOS test orchestration..."
    echo ""

    # Step 1: Setup Java
    log "Checking Java..."
    if ! setup_java; then
        exit 1
    fi

    # Step 2: Check/install Maestro
    log "Checking Maestro..."
    if ! check_maestro; then
        install_maestro || exit 1
    fi

    # Step 3: Check/start backend
    log "Checking backend..."
    if ! check_backend; then
        start_backend || exit 1
    else
        log_success "Backend already running"
    fi

    # Step 4: Check/seed test data
    log "Checking test data..."
    if ! check_test_data; then
        seed_test_data || exit 1
    else
        verbose "Test data already seeded"
    fi

    # Step 5: Check/boot simulator
    log "Checking simulator..."
    if ! check_simulator; then
        boot_simulator || exit 1
    else
        log_success "Simulator already running"
    fi

    # Step 6: Check/build app
    log "Checking app installation..."
    if [ "$REBUILD" = true ] || ! check_app_installed; then
        build_and_install || exit 1
    else
        log_success "App already installed"
    fi

    # Give simulator a moment to settle
    sleep 2

    # Step 7: Run tests
    echo ""
    run_maestro_tests
    exit $?
}

main
