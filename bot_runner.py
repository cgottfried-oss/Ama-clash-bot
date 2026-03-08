import subprocess
import time

print("Starting war tracker...")
war_process = subprocess.Popen(["python", "current_war.py"])

print("Starting monthly leaderboard...")
leaderboard_process = subprocess.Popen(["python", "monthly_leaderboard.py"])

# Keep the runner alive
while True:
    time.sleep(600)