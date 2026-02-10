#!/bin/bash
# Daily LLM/Agent Memory Research Briefing Generator
# Runs every night to generate fresh research reports with deduplication

set -e

# Configuration
DATE=$(date +%Y-%m-%d)
REPORT_DIR="/var/www/html/paper-briefings"
SCRIPT_DIR="/home/admin/Code/web_server"
SKILL_DIR="/home/admin/.openclaw/workspace/skills/arxiv-watcher"
RESEARCH_LOG="/home/admin/.openclaw/workspace/memory/RESEARCH_LOG.md"

# Create directories if they don't exist
mkdir -p "$REPORT_DIR"
mkdir -p "/home/admin/.openclaw/workspace/memory"

# Function to search and collect papers
search_papers() {
    local keyword="$1"
    local count="$2"
    local output_file="$3"
    
    echo "Searching for: $keyword"
    # Use arxiv-watcher to search
    bash "$SKILL_DIR/scripts/search_arxiv.sh" "$keyword" "$count" > "$output_file"
}

# Function to extract paper info from XML
extract_papers() {
    local xml_file="$1"
    local output_file="$2"
    
    # Extract paper information using grep and sed
    # This is a simplified extraction - in production, use proper XML parsing
    grep -A 20 "<entry>" "$xml_file" | grep -E "(<title>|<id>|<published>|<summary>)" | \
    sed 's/<[^>]*>//g' | sed 's/^[[:space:]]*//' | sed '/^$/d' > "$output_file"
}

# Function to check for duplicates
check_duplicates() {
    local new_papers="$1"
    local previous_reports="$2"
    local unique_papers="$3"
    
    if [ ! -f "$previous_reports" ]; then
        cp "$new_papers" "$unique_papers"
        return
    fi
    
    # Simple deduplication by comparing titles
    # In production, this would be more sophisticated
    while IFS= read -r line; do
        if ! grep -q "$line" "$previous_reports"; then
            echo "$line" >> "$unique_papers"
        fi
    done < "$new_papers"
}

# Main execution
echo "Starting daily paper briefing generation for $DATE"

# Search for papers with our keywords
KEYWORDS=("Agentic" "RAG" "Agent" "LLM" "memory" "long-term")
TEMP_DIR="/tmp/daily_briefing_$$"
mkdir -p "$TEMP_DIR"

ALL_PAPERS="$TEMP_DIR/all_papers.txt"
UNIQUE_PAPERS="$TEMP_DIR/unique_papers.txt"
PREVIOUS_REPORTS="$REPORT_DIR/previous_reports.txt"

# Collect papers from all keywords
for keyword in "${KEYWORDS[@]}"; do
    XML_FILE="$TEMP_DIR/${keyword}_papers.xml"
    TXT_FILE="$TEMP_DIR/${keyword}_papers.txt"
    
    search_papers "$keyword" 5 "$XML_FILE"
    extract_papers "$XML_FILE" "$TXT_FILE"
    cat "$TXT_FILE" >> "$ALL_PAPERS"
done

# Remove duplicates
if [ -f "$ALL_PAPERS" ]; then
    check_duplicates "$ALL_PAPERS" "$PREVIOUS_REPORTS" "$UNIQUE_PAPERS"
    
    # Generate HTML report if we have new papers
    if [ -s "$UNIQUE_PAPERS" ]; then
        # Create HTML report (this would be more sophisticated in production)
        REPORT_FILE="$REPORT_DIR/llm-agent-memory-briefing-$DATE.html"
        
        cat > "$REPORT_FILE" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM/Agent Memory Research Briefing - $DATE</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; text-align: center; }
        .paper { background: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 4px solid #007bff; }
        .title { font-weight: bold; color: #333; }
        .date { color: #666; font-size: 0.9em; }
        .summary { color: #444; margin-top: 5px; }
    </style>
</head>
<body>
    <h1>LLM/Agent Memory Research Briefing</h1>
    <p><strong>Date:</strong> $DATE</p>
    <p><strong>New papers found:</strong> $(wc -l < "$UNIQUE_PAPERS")</p>
    
EOF
        
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                cat >> "$REPORT_FILE" << EOF
    <div class="paper">
        <div class="title">$line</div>
        <div class="date">$(date)</div>
        <div class="summary">Summary to be added...</div>
    </div>
EOF
            fi
        done < "$UNIQUE_PAPERS"
        
        cat >> "$REPORT_FILE" << EOF
</body>
</html>
EOF
        
        echo "Report generated: $REPORT_FILE"
        
        # Update previous reports log
        cat "$UNIQUE_PAPERS" >> "$PREVIOUS_REPORTS"
        
        # Also update the research log as required by arxiv-watcher
        if [ -f "$UNIQUE_PAPERS" ]; then
            {
                echo "### [$DATE] Daily LLM/Agent Memory Research Briefing"
                echo "- **New papers**: $(wc -l < "$UNIQUE_PAPERS")"
                echo "- **Keywords**: ${KEYWORDS[*]}"
                echo "- **Report**: [View Report](/paper-briefings/llm-agent-memory-briefing-$DATE.html)"
            } >> "$RESEARCH_LOG"
        fi
    else
        echo "No new papers found. Skipping report generation."
    fi
else
    echo "No papers collected. Skipping report generation."
fi

# Cleanup
rm -rf "$TEMP_DIR"

echo "Daily briefing generation completed for $DATE"