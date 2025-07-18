# Keeper Magic API Design

## Problem
The original Keeper commands like "save", "keep", and "capture" were triggering NVIDIA G-Assist's instant replay feature, making the plugin unusable.

## Solution
Redesigned the API with magical spell-themed commands that avoid gaming-related terminology.

## New Command Structure

### Core Magic Commands

| Old Command | New Command | Description | Example Usage |
|------------|-------------|-------------|---------------|
| `keep_context` | `memorize` | Save current workspace | "memorize realm as project1" |
| `restore_context` | `recall` | Restore saved workspace | "recall project1" |
| `list_contexts` | `grimoire` | List all saved workspaces | "grimoire" |
| `quick_keep` | `snapshot` | Quick save with timestamp | "snapshot" |
| `quick_switch` | `timeshift` | Switch to most recent | "timeshift" |
| `clear_windows` | `vanish` | Save & close all windows | "vanish" |
| `minimize_windows` | `shroud` | Save & minimize all | "shroud" |

### Parameter Changes

- `context_name` → `realm_name` (but supports both for backward compatibility)

### Response Messages

The new commands use thematic responses with emojis:
- ✨ for successful operations
- 🚫 for failures
- 📖 for the grimoire (list)
- 💎 for snapshots
- 🌀 for timeshift
- 🌫️ for vanish
- 🌑 for shroud

## Implementation Details

### Files Created/Modified:
1. **manifest_magic.json** - New manifest with magic commands
2. **plugin_magic.py** - Updated plugin supporting both APIs
3. **test_magic_commands.py** - Test suite for new commands

### Backward Compatibility
The plugin maintains full backward compatibility:
- Old command names still work
- Old parameter names are supported
- Can mix old and new syntax

### Usage Examples

Instead of:
```
"save workspace as test" → Triggers G-Assist
"keep context as project" → Triggers G-Assist
```

Use:
```
"memorize realm as test"
"memorize project"
"snapshot" (for quick save)
"recall test"
"grimoire" (see all realms)
```

## Benefits

1. **No G-Assist Conflicts**: Magic-themed words don't trigger gaming features
2. **Memorable**: Spell metaphors are intuitive and fun
3. **Consistent Theme**: All commands follow magical naming convention
4. **Backward Compatible**: Existing integrations continue to work
5. **Enhanced UX**: Thematic responses make the experience more engaging

## Alternative Command Sets Considered

### Set 1: Fantasy/Magic (Selected)
- memorize, recall, grimoire, snapshot, timeshift, vanish, shroud

### Set 2: Arcane/Mystical
- enchant, summon, chronicle, freeze, portal, dispel, veil

### Set 3: Wizard/Sorcery
- bind, conjure, archive, crystallize, warp, banish, cloak

The first set was chosen for being most intuitive while avoiding any gaming terminology.