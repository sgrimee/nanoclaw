# List all targets
default:
    @just --list

# Start the bot service
start:
    systemctl --user start nanoclaw

# Stop the bot service and all agent containers
stop:
    systemctl --user stop nanoclaw
    -docker rm -f $(docker ps -q --filter ancestor=nanoclaw-agent:latest) 2>/dev/null

# Restart the bot service
restart: stop start

# Show service status and running agent containers
status:
    -systemctl --user --no-pager status nanoclaw
    @echo ""
    @echo "Agent containers:"
    -@docker ps --filter ancestor=nanoclaw-agent:latest

# Enable auto-start on login
enable:
    systemctl --user enable nanoclaw

# Disable auto-start on login
disable:
    systemctl --user disable nanoclaw

# Tail all logs
logs:
    tail -f logs/*.log
