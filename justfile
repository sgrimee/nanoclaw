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

# Tail latest logs and live docker container output
logs:
    #!/usr/bin/env bash
    set -euo pipefail
    pids=()
    declare -A tracked_containers
    declare -A tracked_logs
    trap 'kill "${pids[@]}" 2>/dev/null' EXIT
    # Poll for new log files and containers every 5s
    while true; do
        # Discover latest log file per directory
        for dir in logs groups/*/logs; do
            [ -d "$dir" ] || continue
            latest=$(ls -t "$dir"/*.log 2>/dev/null | head -1) || true
            if [ -n "$latest" ] && [ -z "${tracked_logs[$latest]:-}" ]; then
                tracked_logs[$latest]=1
                tail -f "$latest" &
                pids+=($!)
            fi
        done
        # Discover new containers
        for cid in $(docker ps -q --filter name=nanoclaw-); do
            if [ -z "${tracked_containers[$cid]:-}" ]; then
                tracked_containers[$cid]=1
                name=$(docker inspect "$cid" | jq -r '.[0].Name' | tr -d '/')
                docker logs -f --since 0s "$cid" 2>&1 | sed "s/^/[$name]  /" &
                pids+=($!)
            fi
        done
        sleep 5
    done

env:
    @echo "\n**** Variable definitions\n"
    tail -n +1 groups/*/.env
    @echo "\n\n**** Generated files that will be mounted ==\n"
    tail -n +1 data/env/*/env

# Compile TypeScript host app
build:
    npm run build

# Build agent container image (incremental)
build-container:
    cd container && ./build.sh

# Force a fully clean container rebuild (prunes BuildKit cache to avoid stale COPY layers)
build-container-clean:
    docker builder prune -af
    cd container && ./build.sh
