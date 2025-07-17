import json
import logging
import os
from ctypes import byref, windll, wintypes
from datetime import datetime
from pathlib import Path
from typing import Optional

import psutil
import pygetwindow as gw
import pyperclip

type Response = dict[bool, Optional[str]]
DATA_DIR = Path.home() / ".context_keeper" / "contexts"

LOG_FILE = Path.home() / "context_keeper_plugin.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

INDEX_FILE = Path.home() / ".context_keeper" / "index.json"


def log_context(context_name: str):
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    index = []
    if INDEX_FILE.exists():
        try:
            index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except:
            index = []
    if context_name in index:
        index.remove(context_name)
    index.insert(0, context_name)
    index = index[:10]  # keep recent 10
    INDEX_FILE.write_text(json.dumps(index, indent=2))


def quick_save(*_):
    context_name = "auto-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    save_context({"context_name": context_name})
    log_context(context_name)
    return generate_success_response(f"Quick saved as '{context_name}'")


def quick_switch(*_):
    if not INDEX_FILE.exists():
        return generate_failure_response("No recent contexts available.")
    try:
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except:
        return generate_failure_response("Index file corrupted.")

    if not index:
        return generate_failure_response("Context list is empty.")
    # Restore most recent context
    context_name = index[0]
    return restore_context({"context_name": context_name})


def clear_windows(*_):
    temp_name = "autosave-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    save_context({"context_name": temp_name})
    log_context(temp_name)
    try:
        for w in gw.getWindowsWithTitle(""):
            if w.title.strip():
                w.minimize()
    except Exception as e:
        logging.warning(f"Window minimize failed: {e}")
    return generate_success_response("Context saved and windows minimized.")


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_json(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_context(params=None, *_):
    context_name = params.get("context_name", "unnamed")
    context_path = DATA_DIR / context_name

    # Save environment variables
    env_vars = dict(os.environ)
    write_json(context_path / "env.json", env_vars)

    # Save clipboard
    try:
        clipboard_data = pyperclip.paste()
        (context_path / "clipboard.txt").write_text(clipboard_data, encoding="utf-8")
    except Exception as e:
        logging.warning(f"Failed to save clipboard: {e}")

    # Save window metadata
    try:
        windows = []
        for w in gw.getWindowsWithTitle(""):
            if w.title.strip():
                windows.append(
                    {
                        "title": w.title,
                        "x": w.left,
                        "y": w.top,
                        "width": w.width,
                        "height": w.height,
                        "isMaximized": w.isMaximized,
                        "isMinimized": w.isMinimized,
                    }
                )
        write_json(context_path / "windows.json", windows)
    except Exception as e:
        logging.warning(f"Failed to enumerate windows: {e}")

    logging.info(f"Context '{context_name}' saved.")
    return generate_success_response(f"Context '{context_name}' saved.")


def restore_context(params=None, *_):
    context_name = params.get("context_name", "")
    context_path = DATA_DIR / context_name
    if not context_path.exists():
        return generate_failure_response("Context not found.")

    # Load and set environment variables (note: will only affect this process and children)
    env_data = read_json(context_path / "env.json")
    for k, v in env_data.items():
        os.environ[k] = v

    # Restore clipboard
    try:
        clipboard_data = (context_path / "clipboard.txt").read_text(encoding="utf-8")
        pyperclip.copy(clipboard_data)
    except Exception as e:
        logging.warning(f"Failed to restore clipboard: {e}")

    # Restore window positions
    try:
        win_meta = read_json(context_path / "windows.json")
        current_windows = {
            w.title.strip(): w for w in gw.getWindowsWithTitle("") if w.title.strip()
        }
        for saved in win_meta:
            title = saved["title"]
            win = current_windows.get(title)
            if win:
                win.moveTo(saved["x"], saved["y"])
                win.resizeTo(saved["width"], saved["height"])
                if saved.get("isMaximized"):
                    win.maximize()
                elif saved.get("isMinimized"):
                    win.minimize()
                else:
                    win.restore()
        logging.info(f"Restored {len(win_meta)} window states.")
    except Exception as e:
        logging.warning(f"Window restore failed: {e}")

    logging.info(f"Context '{context_name}' restored.")
    return generate_success_response(f"Context '{context_name}' restored.")


def read_command() -> dict | None:
    try:
        STD_INPUT_HANDLE = -10
        pipe = windll.kernel32.GetStdHandle(STD_INPUT_HANDLE)
        chunks = []

        while True:
            BUFFER_SIZE = 4096
            message_bytes = wintypes.DWORD()
            buffer = bytes(BUFFER_SIZE)
            success = windll.kernel32.ReadFile(
                pipe, buffer, BUFFER_SIZE, byref(message_bytes), None
            )
            if not success:
                return None
            chunk = buffer.decode("utf-8")[: message_bytes.value]
            chunks.append(chunk)
            if message_bytes.value < BUFFER_SIZE:
                break

        return json.loads("".join(chunks))
    except:
        return None


def write_response(response: Response) -> None:
    try:
        STD_OUTPUT_HANDLE = -11
        pipe = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        json_message = json.dumps(response)
        message_bytes = json_message.encode("utf-8")
        message_len = len(message_bytes)
        windll.kernel32.WriteFile(
            pipe, message_bytes, message_len, wintypes.DWORD(), None
        )
    except Exception as e:
        logging.error(f"write error: {e}")


def generate_success_response(message: str = None) -> Response:
    resp = {"success": True}
    if message:
        resp["message"] = message
    return resp


def generate_failure_response(message: str = None) -> Response:
    resp = {"success": False}
    if message:
        resp["message"] = message
    return resp


# === Context Handlers ===


def save_context(params=None, *_):
    context_name = params.get("context_name", "unnamed")
    # Simulated logic
    logging.info(f"Saving context: {context_name}")
    return generate_success_response(f"Saved context: {context_name}")


def restore_context(params=None, *_):
    context_name = params.get("context_name", "")
    logging.info(f"Restoring context: {context_name}")
    return generate_success_response(f"Restored context: {context_name}")


def quick_save(*_):
    context_name = "auto-" + str(int(psutil.boot_time()))
    logging.info("Performing quick save")
    return generate_success_response(f"Quick saved as: {context_name}")


def quick_switch(*_):
    logging.info("Quick switching")
    return generate_success_response("Switched to recent context")


def clear_windows(*_):
    logging.info("Saving then clearing windows")
    return generate_success_response("Context saved and windows cleared")


def execute_initialize_command():
    return generate_success_response("Plugin initialized")


def execute_shutdown_command():
    return generate_success_response("Plugin shutdown")


# === Plugin Loop ===


def main():
    commands = {
        "initialize": execute_initialize_command,
        "shutdown": execute_shutdown_command,
        "save_context": save_context,
        "restore_context": restore_context,
        "quick_save": quick_save,
        "quick_switch": quick_switch,
        "clear_windows": clear_windows,
    }
    cmd = ""
    while cmd != "shutdown":
        input_data = read_command()
        if input_data and "tool_calls" in input_data:
            for call in input_data["tool_calls"]:
                func = call.get("func", "")
                props = call.get("properties", {})
                if func in commands:
                    cmd = func
                    response = commands[func](props)
                else:
                    response = generate_failure_response("Unknown function")
                write_response(response)
        else:
            write_response(generate_failure_response("Malformed input"))


if __name__ == "__main__":
    main()
