# Keeper Plugin for NVIDIA G-Assist

Transform your Windows development workflow with intelligent context management! This plugin lets you keep and restore your complete development environment through the G-Assist platform. Whether you're switching between projects or resuming work sessions, maintaining your perfect development setup has never been easier.

## 🎯 Important: Magic Commands API

To avoid conflicts with G-Assist's gaming features (like instant replay), Keeper uses **magic-themed commands**:

- **`Memorize`** instead of "save" or "keep"
- **`Recall`** instead of "restore" 
- **`Snapshot`** for quick saves
- **`Grimoire`** to list saved contexts
- **`Timeshift`** to switch to recent context
- **`Vanish`** to save & close all
- **`Shroud`** to save & minimize all

Example: Say "Memorize realm as project1" instead of "save workspace as project1"

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

**Saving Contexts (Magic Commands):**
- "Memorize realm as [project-name]"
- "Memorize [project-name]"
- "Snapshot" (quick save with timestamp)

**Restoring Contexts:**
- "Recall [project-name]"
- "Recall my pytorch project"
- "Timeshift" (switch to most recent)

**Management Commands:**
- "Grimoire" (list all saved contexts)
- "Vanish" (save & close all windows)
- "Shroud" (save & minimize all windows)

> **Note**: We use magic-themed commands to avoid conflicts with G-Assist's gaming features. Words like "save", "keep", and "capture" may trigger instant replay recording.

### Example Usage

**Memorizing a Machine Learning Project:**
```
You: "Memorize realm as pytorch-research"
G-Assist: "✨ Realm 'pytorch-research' has been MEMORIZED! ✨"
📚 Windows preserved: 8
🌐 Browser portals: 42
📜 Sacred scrolls (IDE files): 15
🔮 Terminal crystals: 5
🗝️ Enchanted variables: 23
```

**Restoring a Web Development Environment:**
```
You: "Recall react-project"
G-Assist: "✨ Realm 'react-project' has been SUMMONED! ✨"
🪟 Windows conjured: 6
🌐 Browser portals opened: 15
🗝️ Enchanted variables: Restored
📅 Originally cast at: 2025-07-18T10:30:00Z
```

**Quick Save/Restore:**
```
You: "Snapshot"
G-Assist: "💎 Realm CRYSTALLIZED instantly!"
✨ Preserved as: crystal-20250718-103045
🪟 Windows: 12
🌐 Browser portals: 35
⚡ Use 'timeshift' to return instantly!

You: "Timeshift"
G-Assist: "🌀 Recent temporal anchors:"
1. crystal-20250718-103045
2. pytorch-research
3. react-project
⚡ Warping to: crystal-20250718-103045
```

**Viewing All Saved Realms:**
```
You: "Grimoire"
G-Assist: "📖 The Grimoire reveals 5 memorized realms:"
✨ pytorch-research:
  📅 Cast on: 2025-07-18T09:15:00Z
  🪟 Windows: 8, 🌐 Portals: 42

✨ react-project:
  📅 Cast on: 2025-07-17T14:22:00Z
  🪟 Windows: 6, 🌐 Portals: 15
...
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

## Data Structure

Contexts are saved as JSON files in:
```
%USERPROFILE%\Keeper\contexts\[context-name]\
```

Each context includes:
- Window positions and states
- Application configurations
- Environment variable snapshots
- Browser tab organizations
- System state information

## Voice Commands Reference

### Magic Commands (Recommended)
| Command | Description | Example |
|---------|-------------|---------|
| `Memorize [name]` | Save current environment | "Memorize realm as pytorch-research" |
| `Recall [name]` | Restore saved environment | "Recall my web project" |
| `Snapshot` | Quick save with timestamp | "Snapshot" |
| `Timeshift` | Switch to most recent | "Timeshift" |
| `Grimoire` | List all saved realms | "Grimoire" |
| `Vanish` | Save & close all windows | "Vanish" |
| `Shroud` | Save & minimize all windows | "Shroud" |

### Legacy Commands (May trigger G-Assist)
| Command | Description | Note |
|---------|-------------|------|
| `Keep context as [name]` | Save environment | ⚠️ May trigger instant replay |
| `Restore [name]` | Restore environment | ✅ Safe to use |
| `Quick keep` | Auto-save | ⚠️ May trigger instant replay |
| `Save workspace` | Save current setup | ⚠️ Will trigger instant replay |

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
