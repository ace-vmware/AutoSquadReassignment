#! python3

import logging
import re
import sf_api
import os

from slackclient import SlackClient

# Set Logging Level
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# SLACK information
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_VERIFICATION_TOKEN = os.environ["SLACK_VERIFICATION_TOKEN"]
slack_client = SlackClient(SLACK_BOT_TOKEN)


# Simple chat message
def sendMessage(slack_client, msg):
    # make the POST request through the python slack client
    updateMsg = slack_client.api_call(
        "chat.postMessage",
        channel='#ws1_autosquadreassignment',
        text=msg)

    # check if the request was a success
    if updateMsg['ok'] is not True:
        logging.error(updateMsg)
    else:
        logging.debug(updateMsg)

# Flask Server Send Update
def sendUpdate(channel, ts, msg):
    slack_client.api_call("chat.update",
                          channel=channel,
                          ts=ts,
                          blocks=[
                              {
                                  "type": "context",
                                  "elements": [
                                      {
                                          "type": "mrkdwn",
                                          "text": f"*@{msg}*"
                                      }
                                  ]
                              }
                          ])

# Sends block
def sendBlock(slack_client, case_link, case_number, from_squad, to_squad, tse_reassigning,
              priority, support_group, first_response_met, case_age):

    resp = slack_client.api_call("chat.postMessage",
                                 channel="#ws1_autosquadreassignment",
                                 blocks=[
                                     {
                                         "type": "divider"
                                     },
                                     {
                                         "type": "section",
                                         "text": {
                                             "type": "mrkdwn",
                                             "text": f"*Case Reassignment Requested:* <{case_link}|{case_number}> "
                                                     f"\n*From Squad:* {from_squad} ---> *To Squad:* {to_squad}"
                                                     f"\n*TSE Reassigning:* {tse_reassigning}"
                                                     f"\n*Priority:* {priority}"
                                                     f"\n*Support Group:* {support_group}"
                                                     f"\n*First Response:* {first_response_met}"
                                                     f"\n *Case Age:* {case_age}"
                                         }
                                     },
                                     {
                                         "type": "actions",
                                         "elements": [
                                             {
                                                 "type": "button",
                                                 "text": {
                                                     "type": "plain_text",
                                                     "text": "Approve",
                                                     "emoji": True
                                                 },
                                                 "confirm": {
                                                     "title": {
                                                         "type": "plain_text",
                                                         "text": "Halt!"
                                                     },
                                                     "text": {
                                                         "type": "mrkdwn",
                                                         "text": "Approving this reassignment will change this SR's ownership in SalesForce and should only be approved by managers or squad ACEs."
                                                     },
                                                     "confirm": {
                                                         "type": "plain_text",
                                                         "text": "Approve"
                                                     },
                                                     "deny": {
                                                         "type": "plain_text",
                                                         "text": "Cancel"
                                                     }
                                                 },
                                                 "value": "approve_button",
                                                 "style": "primary"
                                             },
                                             {
                                                 "type": "button",
                                                 "text": {
                                                     "type": "plain_text",
                                                     "text": "Deny",
                                                     "emoji": True
                                                 },
                                                 "confirm": {
                                                     "title": {
                                                         "type": "plain_text",
                                                         "text": "Halt!"
                                                     },
                                                     "text": {
                                                         "type": "mrkdwn",
                                                         "text": "Denying this reassignment will leave this SR's ownership to the TSE Reassigning. This action should only be completed by a manger or squad ACE."
                                                     },
                                                     "confirm": {
                                                         "type": "plain_text",
                                                         "text": "Deny"
                                                     },
                                                     "deny": {
                                                         "type": "plain_text",
                                                         "text": "Cancel"
                                                     }
                                                 },
                                                 "value": "deny_button",
                                                 "style": "danger",
                                                 # "url": "https://57357b871079.ngrok.io/slack"
                                             }
                                         ]
                                     }
                                 ]
                                 )
    return resp

def parseSlackEvent(slack_event):
    # Parsing
    message_ts = slack_event.get('container').get('message_ts')
    channel_id = slack_event.get('container').get('channel_id')
    username = slack_event.get('user').get('username')
    template_text = slack_event.get('message').get('blocks')[1].get('text').get('text')
    case_link = re.compile(r'(<.*>)').search(template_text).group()
    case_id = re.compile(r'(?<=r\/Case\/)\d+\w+', re.IGNORECASE).search(template_text).group()
    tse_macro_id = sf_api.get_tse_macro_id(case_id)
    try:
        from_squad = re.compile(r'(?<=\*From Squad:\*\s\s)\s*\w+').findall(template_text)[0]
        to_squad = re.compile(r'(?<=\*To Squad:\*\s\s)\s*\w+').findall(template_text)[0]
    except IndexError as e:
        logging.debug(e)
        from_squad = 'No \'From Squad\''
        to_squad = 'No \'To Squad\''

    slack_event_dict = {"message_ts": message_ts, "channel_id": channel_id, "username": username,
                        "template_text": template_text, "case_link": case_link, "case_id": case_id,
                        "tse_macro_id": tse_macro_id, "from_squad": from_squad, "to_squad": to_squad}
    return slack_event_dict