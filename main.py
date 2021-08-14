import stripe
from simple_salesforce import Salesforce
from flask import Flask, request, Response

import config

stripe.api_key = config.stripe_api_key

# https://github.com/simple-salesforce/simple-salesforce
sf = Salesforce(instance_url=config.sf_instance_url, session_id='')

app = Flask(__name__)

@app.route('/')
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