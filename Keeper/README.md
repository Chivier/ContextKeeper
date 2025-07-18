# Keeper Plugin for NVIDIA G-Assist

Transform your Windows development workflow with intelligent context management! This plugin lets you keep and restore your complete development environment through the G-Assist platform. Whether you're switching between projects or resuming work sessions, maintaining your perfect development setup has never been easier.


## What Can It Do?
- **Complete Environment Capture**: Keep your entire Windows development context including:
  - IDE projects and open files (VSCode, Cursor, JetBrains Suite)
  - Terminal sessions with working directories and environment variables
  - Browser tabs with full organization and grouping
  - Document states (Office, Notion, Obsidian, OneNote)
  - Communication tools (Slack, Discord, Teams, WeChat)
  - System settings (volume, clipboard, window positions)

- **Intelligent Restoration**: Restore your exact development environment with:
  - Precise window positioning and sizing
  - Virtual desktop assignments
  - Environment variable restoration
  - Application state recovery
  - Browser tab groups and organization

- **Voice-Activated Control**: Use natural language commands like:
  - "Save context as pytorch-research"
  - "Restore my machine learning project"
  - "Quick save current setup"

## Before You Start
Make sure you have:
- Windows 10/11 PC
- Python 3.8 or higher installed
- NVIDIA G-Assist installed
- Visual Studio 2022 (for building)
- Administrator privileges (for some system-level operations)

## Installation Guide

### Step 1: Get the Files
```bash
git clone <repository-url>
cd Keeper/src
```
This downloads all the necessary files to your computer.

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```
This installs all required Python packages including:
- `pywin32` for Windows API access
- `psutil` for process management
- `pywinauto` for UI automation
- `requests` for browser debugging protocol
- `Pillow` for favicon processing

### Step 3: Build the Plugin
```bash
python build.py
```
This creates the executable and prepares all necessary files.

### Step 4: Install the Plugin
1. Navigate to the `dist` folder created by the build script
2. Copy the `contextkeeper` folder to:
```bash
%PROGRAMDATA%\NVIDIA Corporation\nvtopps\rise\plugins
```

💡 **Tip**: Make sure all files are copied, including:
- The executable (`g-assist-plugin-keeper.exe`)
- `manifest.json`
- Configuration files

## How to Use

### Basic Commands
Once everything is set up, you can manage your development contexts through simple voice commands:

**Saving Contexts:**
- "Save workspace as [project-name]"
- "Keep context as [project-name]"
- "Memorize realm as [project-name]" (alternative syntax)
- "Quick save" (auto-timestamped)

**Restoring Contexts:**
- "Restore [project-name]"
- "Switch to [project-name]"
- "Quick switch" (to most recent)

**Management Commands:**
- "List contexts" or "Show workspaces"
- "Close windows" (save & close all applications)
- "Minimize all" (save & minimize all windows)
- "Clear history [project-name]" (delete saved context files)
- "Clear all history" (delete all saved context files)

### Example Usage

**Saving a Machine Learning Project:**
```
You: "Save workspace as pytorch-research"
G-Assist: "pytorch-research context KEPT!
Windows: 8
Browser tabs: 42
IDE files: 15
Terminal sessions: 5
Environment variables: 23"
```

**Restoring a Web Development Environment:**
```
You: "Restore react-project"
G-Assist: "react-project context RESTORED!
Windows restored: 6
Browser tabs restored: 15
Environment variables: Restored
Originally kept at: 2025-07-18T10:30:00Z"
```

**Quick Save/Restore:**
```
You: "Quick save"
G-Assist: "Quick save SUCCESSFUL!
Saved as: auto-20250718-103045
Windows: 12
Browser tabs: 35
Use 'Quick switch' to restore instantly!"

You: "Quick switch"
G-Assist: "Recent contexts:
1. auto-20250718-103045
2. pytorch-research
3. react-project

Switching to: auto-20250718-103045"
```

**Managing Saved Contexts:**
```
You: "List contexts"
G-Assist: "Found 5 saved contexts:

pytorch-research:
  Saved: 2025-07-18T09:15:00Z
  Windows: 8, Tabs: 42

react-project:
  Saved: 2025-07-17T14:22:00Z
  Windows: 6, Tabs: 15
..."
```

## Advanced Features

### Environment Variable Management
The plugin automatically keeps and restores:
- PATH configurations
- Development tool paths (Node.js, Python, etc.)
- API keys and tokens
- Virtual environment activations
- Custom environment variables

### Browser Tab Organization
Supports advanced browser features:
- Tab groups and organization
- Pinned tabs
- Active tab tracking
- Cross-browser compatibility (Chrome, Edge, Firefox, Arc)

### Terminal State Preservation
Maintains terminal configurations:
- Working directories for each tab
- Shell types (PowerShell, CMD, WSL)
- Environment variables per session
- Terminal profiles and themes

## Supported Applications

### IDEs and Editors
- Visual Studio Code
- Cursor
- JetBrains Suite (IntelliJ, PyCharm, WebStorm, etc.)
- Visual Studio

### Terminals
- Windows Terminal
- PowerShell
- Command Prompt
- Termius
- WSL environments

### Browsers
- Google Chrome
- Microsoft Edge
- Mozilla Firefox
- Arc Browser

### Document Applications
- Microsoft Office Suite
- Notion
- Obsidian
- OneNote
- Adobe Acrobat

### Communication Tools
- Slack
- Discord
- Microsoft Teams
- WeChat

## Troubleshooting Tips

### Common Issues
- **Context not keeping completely?**
  - Run G-Assist as administrator
  - Check if applications are responding
  - Review the log file for specific errors

- **Browser tabs not restoring?**
  - Ensure browser allows debugging protocol
  - Check browser settings for tab restoration
  - Try closing and reopening the browser

- **Environment variables not working?**
  - Verify administrator privileges
  - Check if variables are system-wide or user-specific
  - Review environment snapshot files

### Logging
The plugin logs all activity to:
```
%USERPROFILE%\keeper.log
```
Check this file for detailed error messages and debugging information.

### Permission Issues
Some operations require elevated privileges:
- System-wide environment variables
- Certain window management operations
- Deep application state access

## Project Structure

The Context Keeper plugin is organized into modular components for maintainability and extensibility:

```
Keeper/
├── plugin.py                      # Main plugin entry point and command handler
├── windows_context_manager.py     # Windows API integration for window management
├── browser_tab_extractor.py       # Browser tab extraction via debugging protocols
├── browser_tab_extractor_fast.py  # Optimized browser tab extraction for quick saves
├── environment_manager.py         # Environment variable capture and restoration
├── terminal_manager.py            # Terminal state preservation (PowerShell, CMD, WSL)
├── ide_tracker.py                 # IDE state tracking (VSCode, JetBrains, etc.)
├── document_tracker.py            # Document state monitoring (Office, Notion, etc.)
├── whitelist_manager.py           # Application whitelist for minimize/close operations
├── quick_response.py              # Fast response handling for better UX
├── manifest.json                  # G-Assist plugin manifest with command definitions
├── requirements.txt               # Python dependencies
├── build.bat                      # Windows build script for creating executable
└── test/                          # Test suite and debugging tools
```

### Core Components

#### `plugin.py`
The main entry point that:
- Implements the G-Assist plugin protocol with named pipe communication
- Routes commands to appropriate handlers (memorize, restore, list, etc.)
- Manages the response format with proper `<<END>>` termination
- Coordinates all subsystem managers

#### `windows_context_manager.py`
Windows-specific functionality:
- Enumerates all visible windows using Win32 API
- Captures window positions, sizes, states, and Z-order (stacking)
- Handles window restoration with proper layering
- Supports minimize/close operations with whitelist protection

#### `browser_tab_extractor.py` & `browser_tab_extractor_fast.py`
Browser integration via debugging protocols:
- Extracts tabs from Chrome, Edge, Firefox
- Captures URLs, titles, and active tab state
- Fast version skips favicon fetching for performance
- Uses browser debugging ports for data access

#### `environment_manager.py`
Environment variable management:
- Captures current environment state
- Creates timestamped snapshots
- Generates restoration scripts (.bat files)
- Handles PATH and custom variables

#### `terminal_manager.py`
Terminal session preservation:
- Detects Windows Terminal, PowerShell, CMD
- Captures working directories per tab
- Preserves shell types and configurations
- Supports multiple terminal applications

#### `ide_tracker.py`
IDE state tracking:
- Monitors VSCode, Cursor, JetBrains IDEs
- Tracks open projects and files
- Captures workspace configurations
- Handles recent project history

#### `document_tracker.py`
Document application monitoring:
- Tracks Office suite documents
- Monitors note-taking apps (Notion, Obsidian)
- Detects unsaved changes
- Supports document restoration

#### `whitelist_manager.py`
Protection list management:
- Maintains list of apps to keep visible
- Default protection for NVIDIA apps and G-Assist
- Persistent whitelist storage
- Runtime add/remove capabilities

## Data Structure

Contexts are saved as JSON files in:
```
%USERPROFILE%\.keeper\contexts\[context-name]\
```

Each context includes:
- Window positions, states, and Z-order
- Application configurations
- Environment variable snapshots
- Browser tab organizations
- System state information

## Voice Commands Reference

### Voice Commands
| Command | Description | Example |
|---------|-------------|---------|
| `Save workspace as [name]` | Save current environment | "Save workspace as pytorch-research" |
| `Keep context as [name]` | Save current environment | "Keep context as web-dev" |
| `Memorize realm as [name]` | Save current environment | "Memorize realm as project-x" |
| `Restore [name]` | Restore saved environment | "Restore my web project" |
| `Quick save` | Auto-timestamped save | "Quick save" |
| `Quick switch` | Switch to most recent | "Quick switch" |
| `List contexts` | Show all saved workspaces | "List contexts" |
| `Close windows` | Save & close all applications | "Close windows" |
| `Minimize all` | Save & minimize all windows | "Minimize all" |
| `Clear history [name]` | Delete saved context files | "Clear history old-project" |
| `Clear all history` | Delete all saved context files | "Clear all history" |
| `Add to whitelist [app]` | Protect app from minimize | "Add Chrome to whitelist" |
| `Remove from whitelist [app]` | Unprotect app | "Remove notepad from whitelist" |
| `List whitelist` | Show protected apps | "List whitelist" |

## Security and Privacy

### Data Protection
- All contexts are kept locally on your machine
- No data is transmitted to external servers
- Environment variables are encrypted when stored
- Sensitive information can be excluded from snapshots

### Permissions
The plugin requires:
- File system access for keeping contexts
- Process enumeration for application detection
- Window management permissions
- Network access for browser tab extraction (local only)

## Performance Considerations

### Optimization Features
- Incremental context keeping
- Background processing for large environments
- Selective application targeting
- Efficient browser tab batching

### Resource Usage
- Minimal memory footprint during idle state
- CPU usage spikes only during keep/restore operations
- Disk usage depends on context complexity
- Network usage limited to local browser debugging

## Want to Contribute?
We'd love your help making this plugin even better! Check out [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute.

## License
This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- Built using Windows APIs for native integration
- Utilizes browser debugging protocols for tab management
- Powered by Python automation libraries
- We use some amazing open-source software to make this work. See [ATTRIBUTIONS.md](ATTRIBUTIONS.md) for the full list.

---

*Streamline your development workflow with Keeper - because your perfect development environment should be just a voice command away!*
