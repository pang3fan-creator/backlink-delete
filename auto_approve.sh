#!/bin/bash
# 自动授权 OpenCode 的权限请求

while true; do
    # 捕获 OpenCode 输出
    output=$(tmux capture-pane -t opencode-session -p -S -20 2>/dev/null)
    
    # 检测权限请求
    if echo "$output" | grep -q "Permission required"; then
        echo "$(date): 检测到权限请求，自动授权..."
        tmux send-keys -t opencode-session "a" Enter
        sleep 2
    fi
    
    sleep 3
done
