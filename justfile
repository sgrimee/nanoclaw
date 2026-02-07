# List all targets
default:
    @just --list

# Start the bot service
start:
    launchctl load ~/Library/LaunchAgents/com.nanoclaw.plist

# Stop the bot service
stop:
    launchctl unload ~/Library/LaunchAgents/com.nanoclaw.plist

# Restart the bot service
restart: stop start

# Tail all logs
logs:
    tail -f logs/*.log
