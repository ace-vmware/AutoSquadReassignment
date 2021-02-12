import slack_api
import sf_api

import json
import logging
import schedule
import time

from flask import Flask, request, make_response, Response

print('Test print to console 3')

# Set Logging Level
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Define Flask App
app = Flask(__name__)

# Verify Token
def verify_slack_token(request_token):
    if slack_api.SLACK_VERIFICATION_TOKEN != request_token:
        print("Error: invalid verification token!")
        print("Received {} but was expecting {}".format(request_token, slack_api.SLACK_VERIFICATION_TOKEN))

        return make_response("Request contains invalid Slack verification token", 403)


@app.route("/slack", methods=["GET", "POST"])
def msg0():
    # Handle GET Requests
    if request.method == 'GET':
        return 'You get a peach.'

    # Handle POST Requests
    if request.method == 'POST':
        # Logging
        slack_event = json.loads(request.form.to_dict(flat=True).get('payload'))
        logging.debug(''.join(['Slack Event: ', str(slack_event)]))
        # Parse Slack Event
        parsed_slack_event = slack_api.parseSlackEvent(slack_event)
        print(parsed_slack_event)

        # Respond to Approve Button
        if slack_event.get('actions')[0].get('value') == 'approve_button':
            # Respond on Slack
            msg = f"{parsed_slack_event['username']} approved reassignment for {parsed_slack_event['case_link']}."
            response = slack_api.sendUpdate(parsed_slack_event['channel_id'], parsed_slack_event['message_ts'], msg)
            # Respond in SalesForce
            sf_api.sf_api_patch(
                parsed_slack_event['case_id'],
                'approved', parsed_slack_event['from_squad'],
                parsed_slack_event['to_squad'])
            # Reassign case in SalesForce
            sf_api.reassign_case_owner(parsed_slack_event['case_id'], parsed_slack_event['to_squad'])

            return Response(response=response,
                            mimetype="application/json",
                            status=200)

        # Respond to Deny Button
        if slack_event.get('actions')[0].get('value') == 'deny_button':
            # Respond on Slack
            msg = f"{parsed_slack_event['username']} denied reassignment for {parsed_slack_event['case_link']}."
            response = slack_api.sendUpdate(parsed_slack_event['channel_id'], parsed_slack_event['message_ts'], msg)
            # Respond in SalesForce
            sf_api.sf_api_patch(
                parsed_slack_event['case_id'],
                'denied', parsed_slack_event['from_squad'],
                parsed_slack_event['to_squad'])
            # Reassign case in SalesForce
            sf_api.reassign_case_owner(parsed_slack_event['case_id'], parsed_slack_event['to_squad'])
            return Response(response=response,
                            mimetype="application/json",
                            status=200)

# Test route for testing Slack slash commands
@app.route("/testasr", methods=["POST"])
def msg1():
    event = request.form
    logging.debug(event)
    return 'Test Completed Successfully'

# Route to respond to Slack challenge
@app.route("/challenge", methods=["POST"])
def msg2():
    """
    This route listens for incoming events from Slack and uses the event
    handler helper function to route events to our Bot.
    """
    slack_challenge_event = request.get_json()

    # ============= Slack URL Verification ============ #
    # In order to verify the url of our endpoint, Slack will send a challenge
    # token in a request and check for this token in the response our endpoint
    # sends back.
    #       For more info: https://api.slack.com/events/url_verification
    if "challenge" in slack_challenge_event:
        return make_response(slack_challenge_event["challenge"], 200, {"content_type": "application/json"})


# Start the Flask server
if __name__ == '__main__':
    app.debug = True
    # app.run(host='0.0.0.0', port=323)
    app.run()
