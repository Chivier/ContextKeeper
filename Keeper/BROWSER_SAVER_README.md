# Browser Tab Saver

A JSON-based browser tab saving and restoration system for Chrome, Edge, and Firefox.

## Features

- **Save all browser tabs to JSON** - Captures URLs, titles, and metadata
- **Restore tabs from JSON** - Reopens saved tabs in their respective browsers
- **Multiple session support** - Save different browsing contexts separately
- **Auto-generated session names** - Quick save without thinking about names
- **Cross-browser support** - Works with Chrome, Edge, and Firefox

## Usage

### Basic Usage

```python
from browser_tab_saver import BrowserTabSaver

# Create saver instance
saver = BrowserTabSaver()

# Save all browser tabs
result = saver.save_all_tabs("work_session")

# Restore tabs later
saver.restore_tabs("work_session")
```

### Command Line Usage

```bash
# Save tabs
python browser_commands.py save my_session

# List saved sessions
python browser_commands.py list

# Restore tabs
python browser_commands.py restore my_session

# Delete a session
python browser_commands.py delete my_session
```

### Quick Save (Auto-named)

```python
# Save with auto-generated timestamp name
result = saver.save_all_tabs()
print(f"Saved as: {result['session_name']}")
# Output: Saved as: tabs_20250719_061530
```

## Requirements

For best results, launch browsers with debugging enabled:

**Chrome:**
```bash
chrome.exe --remote-debugging-port=9222
```

**Edge:**
```bash
msedge.exe --remote-debugging-port=9223
```

**Firefox:**
- Works by reading session files (no special launch needed)

## JSON Format

Saved sessions are stored in `~/.keeper/browser_tabs/` as JSON files:

```json
{
  "session_name": "work_session",
  "timestamp": "2025-07-19T10:30:00",
  "browsers": {
    "chrome": [
      {
        "url": "https://example.com",
        "title": "Example Page",
        "favicon": "",
        "active": true,
        "index": 0
      }
    ],
    "edge": [...]
  },
  "metadata": {
    "total_tabs": 15,
    "browsers_found": ["chrome", "edge"]
  }
}
```

## API Reference

### BrowserTabSaver Methods

- `save_all_tabs(session_name=None)` - Save all browser tabs
- `restore_tabs(session_name, browser=None)` - Restore saved tabs
- `list_saved_sessions()` - List all saved sessions
- `get_session_details(session_name)` - Get detailed session info
- `delete_session(session_name)` - Delete a saved session

## Examples

See `browser_saver_example.py` for more usage examples.