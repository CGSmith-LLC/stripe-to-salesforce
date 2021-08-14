import os, json, logging

import requests, stripe
from simple_salesforce import Salesforce
from flask import Flask, request, Response


app = Flask(__name__)
if 'logs' not in os.listdir(os.getcwd()):
    os.mkdir('logs')

application_path = os.path.dirname(os.path.abspath(__file__))
config = json.load(open(os.path.join(application_path, 'config.json')))
sf_auth_slug = config['sf_auth_slug']
sf_webhook_slug = config['sf_webhook_slug']

# # https://github.com/simple-salesforce/simple-salesforce
stripe.api_key = config['stripe_api_key']
sf = Salesforce(instance_url=config.sf_instance_url, session_id='')

app = Flask(__name__)


@app.route(sf_webhook_slug)
def payment_to_salesforce():

    data = dict(request.form)

    # Create the event object from the payload
    # https://stripe.com/docs/payments/handling-payment-events#create-webhook
    try:
        event = stripe.Event.construct_from(data, stripe.api_key)
    except ValueError:
        return Response('Invalid payload', status=400)

    # Process the new charge event
    if event.type == 'charge.succeeded':
        charge = event.data.object  # Charge obj: https://stripe.com/docs/api/charges/object

        # When the new subscription is added, it will create the charge.succeeded event as well (along with
        # customer.subscription.created event). Learn more: https://stripe.com/docs/api/events

        # todo Create a Salesforce opportunity
        # https://developer.salesforce.com/docs/atlas.en-us.sfFieldRef.meta/sfFieldRef/salesforce_field_reference_Opportunity.htm
        sf.Opportunity.create({
            'AccountId': '',
            'Name': '',
            'Description': 'Payment from ' + charge.billing_details.name,
            'Amount': charge.amount,
            'LeadSource': '',
            'Probability': '',
            'Type': ''
        })

    return Response(status=400)


@app.route(sf_auth_slug)
def salesforce_authorization():
    # Create a Connected App on Salesforce to get the client ID and secret:
    # https://help.salesforce.com/s/articleView?id=sf.connected_app_create.htm&type=5

    # Salesforce OAuth 2.0 API reference:
    # https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_web_server_flow.htm&type=5
    # another API reference:
    # https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/quickstart.htm

    # Update the log parameters with the new filename
    reportName = os.path.join('logs', 'log ' + datetime.datetime.now().strftime('%Y-%m') + '.txt')
    logging.basicConfig(filename=reportName, level=logging.INFO, format=' %(asctime)s -  %(levelname)s -  %(message)s')

    # Read the config file
    config = json.load(open(os.path.join(application_path, 'config.json')))

    token = config.get('access_token')

    if token:
        logging.info('The app authorization url is called but the app is already authorized')
        return 'The app is already authorized'
    else:
        # Check if user returned from the authorization page with the code
        authCode = request.args.get('code')
        if authCode:
            # Send the code to get the access token
            data = {
                'grant_type': 'authorization_code',
                'code': authCode,
                'client_id': config["sf_consumer_key"],
                'client_secret': config["sf_consumer_secret"],
                'redirect_uri': config["app_address"] + config["sf_auth_slug"]
            }
            response = requests.post('https://godschild.lightning.force.com/services/oauth2/token', data=data)

            try:
                config['access_token'] = response.json()['access_token']
            except:
                logging.error(str(response.json()))
                raise Exception('error getting the token from the response')

            # Save the access token
            json.dump(config, open(os.path.join(application_path, 'config.json'), 'w'))

            logging.info('The app got authorized')

            return f'The app is authorized.'

        else:
            # send the authorization request to get the code
            redirectUrl = f'https://login.salesforce.com/services/oauth2/authorize?' \
                          f'response_type=code&' \
                          f'client_id={config["sf_consumer_key"]}&' \
                          f'redirect_uri={config["app_address"]}{config["sf_auth_slug"]}&' \
                          f'scope=full'
            logging.info('The app authorization url is called, no token found. Redirecting to ' + redirectUrl)
            return redirect(redirectUrl)