import pyautogui
import requests
import time
import cv2
import numpy as np
import os
import psutil
import subprocess
import pygetwindow as gw
import json
import threading
import discord

# === SETTINGS ===
IMAGE_FOLDER = "disconnect_screens"
RUST_PROCESS_NAME = "RustClient.exe"
RUST_STEAM_APP_ID = "steam://rungameid/252490"

# Defaults used when config file does not exist
DEFAULT_SERVER_IP = "connect vanilla.rustoria.us:28010"
DEFAULT_WEBHOOK = ""
DEFAULT_TOKEN = ""

CONFIG_FILE = "config.json"


DEFAULT_CONFIG = {
    "server_ip": DEFAULT_SERVER_IP,
    "webhook": DEFAULT_WEBHOOK,
    "token": DEFAULT_TOKEN,
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(data)
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


config = load_config()


# === UTILITY FUNCTIONS ===

def log(message):
    print(message)
    webhook = config.get("webhook")
    if not webhook:
        return
    try:
        requests.post(webhook, json={"content": message})
    except Exception as e:
        print(f"Failed to send webhook: {e}")


def is_rust_running():
    return any(proc.name() == RUST_PROCESS_NAME for proc in psutil.process_iter())



def launch_rust():
    log("🟡 Launching Rust...")
    subprocess.Popen(["start", RUST_STEAM_APP_ID], shell=True)


def close_rust():
    """Gracefully close Rust using the in-game console."""
    pyautogui.press('f1')
    time.sleep(1)
    pyautogui.typewrite('quit')
    pyautogui.press('enter')

def load_templates(folder):
    templates = []
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            templates.append(cv2.imread(path, 0))
    return templates

def match_any_template(screen_gray, templates, threshold=0.8):
    for template in templates:
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        if (result >= threshold).any():
            return True
    return False

def is_disconnected(templates):
    try:
        screen = pyautogui.screenshot()
        screen_np = np.array(screen)
        screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_BGR2GRAY)
        return match_any_template(screen_gray, templates)
    except Exception as e:
        log(f"❌ is_disconnected() error: {e}")
        return False


def try_click_specific(image_path, retries=3, delay=1):
    for attempt in range(retries):
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=0.7)
            if location:
                pyautogui.moveTo(location.left + location.width // 2, location.top + location.height // 2)
                pyautogui.click()
                log(f"✅ Clicked: {image_path}")
                return True
        except Exception as e:
            log(f"❌ Error clicking {image_path} (attempt {attempt+1}): {e}")
        time.sleep(delay)
    log(f"❌ Could not find: {image_path}")
    return False


def try_click_any_button(folder):
    log(f"🔎 Searching for buttons in: {folder}")
    for filename in os.listdir(folder):
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue
        path = os.path.join(folder, filename)
        location = pyautogui.locateOnScreen(path, confidence=0.7)
        if location:
            pyautogui.moveTo(location.left + location.width // 2, location.top + location.height // 2)
            pyautogui.click()
            log(f"✅ Clicked button: {filename}")
            return True
    return False


def is_loading_into_server(templates):
    screen = pyautogui.screenshot()
    screen_np = np.array(screen)
    screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_BGR2GRAY)
    return match_any_template(screen_gray, templates)

def wait_for_server_loading(templates, timeout=30):
    log("⏳ Waiting for loading screen...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_loading_into_server(templates):
            log("🚀 Server loading detected.")
            return True
        time.sleep(2)
    log("❌ Loading screen not detected in time.")
    return False


def connect_via_console(ip):
    try:
        log("🧭 Connecting via F1 console...")
        pyautogui.press('f1')  # Open console
        time.sleep(1)

        pyautogui.typewrite(ip)
        pyautogui.press('enter')
        time.sleep(2)

        pyautogui.press('f1')  # Close console
        log("⌛ Waiting to detect loading screen...")

        for _ in range(30):  # Check for 30 seconds
            try:
                if is_loading_into_server(load_templates("f1_loading_screens")):
                    log("✅ Server loading detected.")
                    return True
            except Exception as inner_e:
                log(f"❌ Error checking loading screen: {inner_e}")
            time.sleep(1)

        log("❌ Loading screen not detected in time.")
        return False
    except Exception as e:
        log(f"❌ connect_via_console() error: {e}")
        return False







def is_dead():
    try:
        templates = load_templates("death_screens")
        screen = pyautogui.screenshot()
        screen_np = np.array(screen)
        screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_BGR2GRAY)
        return match_any_template(screen_gray, templates)
    except Exception as e:
        log(f"❌ is_dead() error: {e}")
        return False


def try_click_respawn():
    log("☠️ Trying to click respawn...")
    for img in ["respawn_button.png", "respawn2_button.png"]:
        location = pyautogui.locateOnScreen(img, confidence=0.8)
        if location:
            pyautogui.moveTo(location.left + location.width // 2, location.top + location.height // 2)
            pyautogui.click()
            log(f"✅ Clicked {img}")
            return True
    log("❌ Respawn button not found.")
    return False

def is_asleep():
    try:
        templates = load_templates("asleep_screens")
        screen = pyautogui.screenshot()
        screen_np = np.array(screen)
        screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_BGR2GRAY)
        return match_any_template(screen_gray, templates)
    except Exception as e:
        log(f"❌ is_asleep() error: {e}")
        return False


def try_click_to_wake():
    log("😴 Trying to wake up...")
    pyautogui.click()
    time.sleep(1)

def is_in_game():
    templates = load_templates("ingame_screens")
    screen = pyautogui.screenshot()
    screen_np = np.array(screen)
    screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_BGR2GRAY)
    return match_any_template(screen_gray, templates)

def do_360_turn():
    log("🔄 Doing 360 turn...")
    pyautogui.mouseDown(button='right')  # Hold right-click to aim
    width, height = pyautogui.size()
    y = height // 2
    start_x = width // 3
    end_x = (width * 2) // 3
    steps = 50

    for i in range(steps):
        x = start_x + (end_x - start_x) * (i / steps)
        pyautogui.moveTo(x, y, duration=0.02)

    pyautogui.mouseUp(button='right')


import random

def simulate_human_movement():
    log("🎮 Simulating human-like activity...")

    # 1. Do a 360-degree turn
    do_360_turn()

    # 2. Jiggle or look up/down
    if random.random() < 0.7:
        log("🧠 Jiggle head...")
        pyautogui.moveRel(20, 0, duration=0.2)
        pyautogui.moveRel(-40, 0, duration=0.2)
        pyautogui.moveRel(20, 0, duration=0.2)

    if random.random() < 0.5:
        log("👀 Look up/down...")
        pyautogui.moveRel(0, random.choice([-40, 40]), duration=0.3)

    # 3. Walk a little with WASD
    if random.random() < 0.6:
        simulate_wasd_movement()

    # 4. Maybe crouch or jump
    if random.random() < 0.4:
        action = random.choice(['ctrl', 'space'])
        log(f"🔘 Pressing {action}")
        pyautogui.keyDown(action)
        time.sleep(0.2)
        pyautogui.keyUp(action)

    log("✅ Done simulating movement.")

def is_steam_update_window_open():
    titles = gw.getAllTitles()
    return any("rust" in title.lower() and "update" in title.lower() for title in titles)


def simulate_wasd_movement():
    log("🏃 Simulating WASD movement...")

    directions = ['w', 'a', 's', 'd']
    move_count = random.randint(1, 3)  # Do 1–3 movements

    for _ in range(move_count):
        key = random.choice(directions)
        duration = random.uniform(1, 3)  # 1 to 3 seconds
        log(f"➡️ Moving {key.upper()} for {duration:.1f}s")

        pyautogui.keyDown(key)
        time.sleep(duration)
        pyautogui.keyUp(key)

        # Optional delay between moves
        time.sleep(random.uniform(0.5, 1))

f1_templates = load_templates("f1_loading_screens")  # Make sure this folder exists

# === MAIN LOOP ===
def automation_loop():
    global running
    log("🟢 Rust Auto-Reconnect Script Started")
    disconnect_templates = load_templates(IMAGE_FOLDER)

    while running:
        if not is_rust_running():
            log("🚫 Rust not running. Attempting to launch...")

            launch_attempts = 0
            while running and not is_rust_running():
                if is_steam_update_window_open():
                    log("🛠️ Rust is updating via Steam. Waiting for update to complete...")
                else:
                    log("🟡 Launching Rust...")
                    launch_rust()

                launch_attempts += 1
                if launch_attempts > 10:
                    log("❌ Tried launching Rust 10 times. Something might be wrong.")
                    break

                time.sleep(30)  # Wait 30 seconds between retries

            if is_rust_running():
                log("✅ Rust successfully launched.")
            continue

        if is_dead():
            log("☠️ Dead detected. Clicking respawn...")
            try_click_respawn()
            time.sleep(10)
            continue

        if is_asleep():
            log("😴 Asleep detected. Clicking to wake...")
            try_click_to_wake()
            time.sleep(5)
            continue

        if is_in_game():
            log("✅ Fully awake. Simulating movement...")
            simulate_human_movement()
            time.sleep(random.randint(45, 75))  # Random cooldown between movements
            continue



        if is_disconnected(disconnect_templates):
            log("⚠️ Disconnected. Reconnecting via console...")
            ip = config.get("server_ip", DEFAULT_SERVER_IP)
            if connect_via_console(ip):
                log("🎮 Reconnect flow complete.")
                time.sleep(30)
            else:
                log("❌ Failed to reconnect. Retrying...")
                time.sleep(10)
            continue

        log("🤔 Unknown state. Waiting 30 seconds...")
        time.sleep(30)


running = False


def start_thread():
    thread = threading.Thread(target=automation_loop, daemon=True)
    thread.start()


intents = discord.Intents.default()
bot = discord.Bot(intents=intents)


@bot.event
async def on_ready():
    log(f"🤖 Bot is online as {bot.user}")


@bot.slash_command(description="Start the automation loop")
async def start(ctx: discord.ApplicationContext):
    global running
    if running:
        await ctx.send("Bot is already running.")
        return
    running = True
    start_thread()
    ip = config.get("server_ip", DEFAULT_SERVER_IP)
    if not is_rust_running():
        log("🟡 Launching Rust before connecting...")
        launch_rust()
        time.sleep(20)
    connect_via_console(ip)
    await ctx.send("🟢 Started automation and connecting to default server.")


@bot.slash_command(description="Stop the automation loop and close Rust")
async def stop(ctx: discord.ApplicationContext):
    global running
    running = False
    close_rust()
    await ctx.send("🔴 Stopped automation and closed Rust.")


@bot.slash_command(description="Join a new Rust server by IP")
async def join(ctx: discord.ApplicationContext, ip: str):
    if not is_rust_running():
        log("🟡 Launching Rust before joining new server...")
        launch_rust()
        time.sleep(20)
    else:
        pyautogui.press('f1')
        time.sleep(1)
        pyautogui.typewrite('disconnect')
        pyautogui.press('enter')
        pyautogui.press('f1')
        for _ in range(30):
            if not is_in_game():
                break
            time.sleep(1)
    connect_via_console(ip)
    config["server_ip"] = ip
    save_config(config)
    await ctx.send(f"🔁 Joined new server: {ip}")


@bot.slash_command(description="Set default server IP")
async def setserver(ctx: discord.ApplicationContext, ip: str):
    config["server_ip"] = ip
    save_config(config)
    await ctx.send(f"✅ Set default server IP to {ip}")


@bot.slash_command(description="Set Discord webhook URL")
async def webhook(ctx: discord.ApplicationContext, url: str):
    config["webhook"] = url
    save_config(config)
    await ctx.send("✅ Webhook set.")


TOKEN = config.get("token") or os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        log("❌ Discord token not provided. Running without bot.")
        running = True
        automation_loop()
