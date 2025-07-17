# Context Keeper Plugin for NVIDIA G-Assist

Transform your Windows development workflow with intelligent context management! This plugin lets you save and restore your complete development environment through the G-Assist platform. Whether you're switching between projects or resuming work sessions, maintaining your perfect development setup has never been easier.

## What Can It Do?
- **Complete Environment Capture**: Save your entire Windows development context including:
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
cd ContextKeeper/src
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
- The executable (`g-assist-plugin-contextkeeper.exe`)
- `manifest.json`
- Configuration files

## How to Use

### Basic Commands
Once everything is set up, you can manage your development contexts through simple voice commands:

**Saving Contexts:**
- "Save context as [project-name]"
- "Quick save current setup"
- "Save my development environment"

**Restoring Contexts:**
- "Restore [project-name]"
- "Load my pytorch project"
- "Switch to web development context"

**Management Commands:**
- "List saved contexts"
- "Clear current windows"
- "Quick switch" (shows recent contexts)

### Example Usage

**Saving a Machine Learning Project:**
```
You: "Save context as pytorch-research"
G-Assist: "Saving context 'pytorch-research'..."
✓ Saved 8 windows
✓ Saved 42 browser tabs
✓ Saved 5 terminal sessions
✓ Saved 23 environment variables
✓ Context saved successfully!
```

**Restoring a Web Development Environment:**
```
You: "Restore my react project"
G-Assist: "Restoring 'react-project' context..."
✓ Restored VSCode workspace
✓ Restored 3 terminal tabs
✓ Restored 15 browser tabs
✓ Restored environment variables
✓ Context restored successfully!
```

## Advanced Features

### Environment Variable Management
The plugin automatically saves and restores:
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
- **Context not saving completely?**
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
%USERPROFILE%\contextkeeper.log
```
Check this file for detailed error messages and debugging information.

### Permission Issues
Some operations require elevated privileges:
- System-wide environment variables
- Certain window management operations
- Deep application state access

## Data Structure

Contexts are saved as JSON files in:
```
%USERPROFILE%\ContextKeeper\contexts\[context-name]\
```

Each context includes:
- Window positions and states
- Application configurations
- Environment variable snapshots
- Browser tab organizations
- System state information

## Voice Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `Save context as [name]` | Save current environment | "Save context as pytorch-research" |
| `Restore [name]` | Restore saved environment | "Restore my web project" |
| `Quick save` | Auto-save with timestamp | "Quick save current setup" |
| `Quick switch` | Show recent contexts | "Quick switch to another project" |
| `List contexts` | Show all saved contexts | "List my saved contexts" |
| `Clear windows` | Close all windows safely | "Clear current windows" |
| `Save tabs only` | Save only browser tabs | "Save my browser tabs" |
| `Save layout only` | Save only window positions | "Save current window layout" |
| `Restore tabs only` | Restore only browser tabs | "Restore my browser tabs" |
| `Restore layout only` | Restore only window positions | "Restore current window layout" |

## Security and Privacy

### Data Protection
- All contexts are saved locally on your machine
- No data is transmitted to external servers
- Environment variables are encrypted when stored
- Sensitive information can be excluded from snapshots

### Permissions
The plugin requires:
- File system access for saving contexts
- Process enumeration for application detection
- Window management permissions
- Network access for browser tab extraction (local only)

## Performance Considerations

### Optimization Features
- Incremental context saving
- Background processing for large environments
- Selective application targeting
- Efficient browser tab batching

### Resource Usage
- Minimal memory footprint during idle state
- CPU usage spikes only during save/restore operations
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

*Streamline your development workflow with Context Keeper - because your perfect development environment should be just a voice command away!*
