# Context Keeper Plugin Troubleshooting Guide

## G-Assist Not Recognizing Commands

If G-Assist isn't recognizing your Context Keeper commands, follow these steps:

### 1. Verify Plugin Installation

The plugin must be installed in the correct directory:
```
%PROGRAMDATA%\NVIDIA Corporation\nvtopps\rise\plugins\context-keeper\
```

This typically resolves to:
```
C:\ProgramData\NVIDIA Corporation\nvtopps\rise\plugins\context-keeper\
```

**Check that this folder contains:**
- `g-assist-plugin-contextkeeper.exe`
- `manifest.json`
- Any other required files

### 2. Rebuild and Install the Plugin

```batch
# From the context-keeper directory:
cd C:\Users\yao\ContextKeeper\context-keeper

# Build the plugin
build.bat

# Copy to G-Assist plugins directory
xcopy /E /Y dist\context-keeper "%PROGRAMDATA%\NVIDIA Corporation\nvtopps\rise\plugins\context-keeper\"
```

### 3. Restart G-Assist

After installing the plugin:
1. Close G-Assist completely (check system tray)
2. Restart G-Assist
3. The plugin should be automatically discovered

### 4. Test with Specific Commands

Try these exact phrases with G-Assist:

**For saving:**
- "save workspace as project1"
- "quick save everything"
- "save my current setup"
- "keep workspace as work"

**For restoring:**
- "restore workspace project1"
- "switch to work workspace"
- "load my saved workspace"

**For listing:**
- "list workspaces"
- "show my workspaces"
- "what workspaces do I have"

### 5. Check Plugin Logs

Plugin logs are saved to:
```
%USERPROFILE%\context_keeper_plugin.log
```

Check this file for any errors or issues.

### 6. Verify Plugin Communication

The plugin uses Windows pipes to communicate with G-Assist. If there are communication issues:

1. Run the plugin directly to test:
```batch
cd "%PROGRAMDATA%\NVIDIA Corporation\nvtopps\rise\plugins\context-keeper"
g-assist-plugin-contextkeeper.exe
```

2. You should see it waiting for input. Press Ctrl+C to exit.

### 7. Common Issues and Solutions

**Issue: "I'm a compact, efficient Nvidia GPU technical assistant..."**
- **Cause**: G-Assist isn't recognizing the plugin command
- **Solution**: Use more specific keywords from the manifest descriptions

**Issue: Plugin not loading**
- **Cause**: Wrong directory or missing files
- **Solution**: Verify installation path and all files are present

**Issue: Commands work but fail**
- **Cause**: Permission issues or missing dependencies
- **Solution**: Run G-Assist as administrator temporarily to test

### 8. Natural Language Tips

G-Assist uses AI to interpret commands. Help it understand by:
- Using keywords from the manifest descriptions
- Being specific about what you want to save/restore
- Using "workspace" or "context" in your commands

### Example Command Variations

Instead of: "help me quick save everything to space-1"
Try:
- "quick save everything"
- "save workspace as space-1"
- "keep context as space-1"

Instead of: "list workspaces"
Try:
- "show my workspaces"
- "list saved workspaces"
- "what workspaces do I have"

### 9. Debug Mode

To see what G-Assist is interpreting:
1. Check G-Assist logs (if available)
2. Use the plugin log file to see if commands are reaching the plugin
3. Test with exact function names first: "keep_context test"

### 10. If Nothing Works

1. Completely uninstall and reinstall the plugin
2. Check Windows Event Viewer for any errors
3. Ensure no antivirus is blocking the plugin
4. Try running a simple test plugin first to verify G-Assist plugin system works