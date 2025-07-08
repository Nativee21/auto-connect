import discord
from discord.ext import commands
import os
import json
import time
import threading
import pyautogui
import psutil
import subprocess
import requests
import cv2
import numpy as np
import pygetwindow as gw

# ========== Configuration ==========
CONFIG_FILE = "config.json"
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"server_ip": "", "webhook": ""}
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)
def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)
config = load_config()

# ========== Logging ==========
def log(msg):
    print(msg)
    if config.get("webhook"):
        try:
            requests.post(config["webhook"], json={"content": msg})
        except: pass

# ========== Rust Control ==========
RUST_PROCESS_NAME = "RustClient.exe"
RUST_STEAM_APP_ID = "steam://rungameid/252490"
def is_rust_running():
    return any(proc.name() == RUST_PROCESS_NAME for proc in psutil.process_iter())
def launch_rust():
    subprocess.Popen(["start", RUST_STEAM_APP_ID], shell=True)
def close_rust():
    pyautogui.press('f1')
    time.sleep(1)
    pyautogui.typewrite('quit')
    pyautogui.press('enter')

def connect_via_f1(ip):
    pyautogui.press('f1')
    time.sleep(1)
    pyautogui.typewrite(f'connect {ip}')
    pyautogui.press('enter')
    time.sleep(1)
    pyautogui.press('f1')
    log(f"🔌 Connecting to {ip}")

def is_loading():
    return match_templates(load_templates("f1_loading_screens"))
def is_disconnected():
    return match_templates(load_templates("disconnect_screens"))
def is_dead():
    return match_templates(load_templates("death_screens"))
def is_asleep():
    return match_templates(load_templates("asleep_screens"))
def is_in_game():
    return match_templates(load_templates("ingame_screens"))

def try_click_respawn():
    for img in ["respawn_button.png", "respawn2_button.png"]:
        loc = pyautogui.locateOnScreen(img, confidence=0.8)
        if loc:
            pyautogui.moveTo(loc.left + loc.width // 2, loc.top + loc.height // 2)
            pyautogui.click()
            log(f"✅ Clicked {img}")
            return True
    return False

def wake_up():
    pyautogui.click()
    time.sleep(1)

def simulate_activity():
    pyautogui.mouseDown(button='right')
    for x in range(400, 800, 10):
        pyautogui.moveTo(x, 540)
        time.sleep(0.01)
    pyautogui.mouseUp()
    pyautogui.moveRel(20, 0)
    pyautogui.moveRel(-40, 0)
    pyautogui.moveRel(20, 0)
    pyautogui.keyDown('w'); time.sleep(1); pyautogui.keyUp('w')
    pyautogui.keyDown('space'); time.sleep(0.1); pyautogui.keyUp('space')
    log("🎮 Simulated activity")

def load_templates(folder):
    return [cv2.imread(os.path.join(folder, f), 0) for f in os.listdir(folder) if f.endswith(('png','jpg'))]

def match_templates(templates):
    try:
        screen = pyautogui.screenshot()
        gray = cv2.cvtColor(np.array(screen), cv2.COLOR_BGR2GRAY)
        for template in templates:
            res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            if (res >= 0.8).any():
                return True
    except: pass
    return False

# ========== Automation Thread ==========
running = False

def bot_loop():
    global running
    while running:
        if not is_rust_running():
            log("🟡 Rust not running. Launching...")
            launch_rust()
            time.sleep(20)
            continue
        if is_disconnected():
            log("🔁 Reconnecting via console...")
            connect_via_f1(config.get("server_ip", ""))
            time.sleep(20)
            continue
        if is_dead():
            try_click_respawn()
            time.sleep(10)
            continue
        if is_asleep():
            wake_up()
            time.sleep(5)
            continue
        if is_in_game():
            simulate_activity()
            time.sleep(60)
            continue
        time.sleep(15)

# ========== Discord Bot ==========
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    log(f"🤖 Bot is online as {bot.user}")

@bot.command()
async def start(ctx):
    global running
    if running:
        await ctx.send("Bot is already running.")
        return
    running = True
    threading.Thread(target=bot_loop, daemon=True).start()
    await ctx.send("🟢 Started automation.")

@bot.command()
async def stop(ctx):
    global running
    running = False
    close_rust()
    await ctx.send("🔴 Stopped automation and closed Rust.")

@bot.command()
async def join(ctx, ip):
    global running
    if not is_rust_running():
        log("🟡 Launching Rust before joining new server...")
        launch_rust()
        time.sleep(20)
    pyautogui.press('f1'); time.sleep(1)
    pyautogui.typewrite('disconnect'); pyautogui.press('enter')
    time.sleep(5)
    connect_via_f1(ip)
    config["server_ip"] = ip
    save_config(config)
    await ctx.send(f"🔁 Joined new server: {ip}")

@bot.command()
async def setserver(ctx, ip):
    config["server_ip"] = ip
    save_config(config)
    await ctx.send(f"✅ Set default server IP to {ip}")

@bot.command()
async def webhook(ctx, url):
    config["webhook"] = url
    save_config(config)
    await ctx.send("✅ Webhook set.")

# ========== Launch Bot ==========
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
