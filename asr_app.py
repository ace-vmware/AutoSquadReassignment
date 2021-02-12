#! python3
import logging
import schedule
import time
import sf_api

# Set Logging Level
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Manual Execution --- replace minutes argument
sf_api.slackPost(30)

# Schedule Jobs
schedule.every(1800).seconds.do(sf_api.slackPost, 30)

while True:
    schedule.run_pending()
    time.sleep(5)  # sleep for 5 seconds between checks on the scheduler
