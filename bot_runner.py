import time
import subprocess

while True:
    print("Running current war tracker...")
    subprocess.run(["python", "current_war.py"])

    print("Running leaderboard update...")
    subprocess.run(["python", "monthly_leaderboard.py"])

    print("Sleeping 10 minutes...")
    time.sleep(600)
