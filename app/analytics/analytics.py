import sys
import httplib2
from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
#from ..settings import GOOGLE_SERVICE_ACCOUNT_EMAIL, GOOGLE_ANALYTICS_PROFILE_ID
GOOGLE_SERVICE_ACCOUNT_EMAIL = '313493436749@developer.gserviceaccount.com' #TODO: Get cameron to create this
GOOGLE_ANALYTICS_PROFILE_ID = 'ga:57774950' #Todo:change this to writehere.com

def get_service():
    f = file('app/analytics/newkey.p12', 'rb')
    key = f.read()
    f.close()

    credentials = SignedJwtAssertionCredentials(
        GOOGLE_SERVICE_ACCOUNT_EMAIL,
        key,
        scope='https://www.googleapis.com/auth/analytics')
    http = httplib2.Http()
    http = credentials.authorize(http)
    return build("analytics", "v3", http=http)

def get_visitors_by_country(service):
    return service.data().ga().get(
        ids=GOOGLE_ANALYTICS_PROFILE_ID,
        start_date='2013-01-01',
        end_date='2013-03-15',
        metrics='ga:visits',
        dimensions='ga:country',
        sort='-ga:visits').execute()

def get_first_profile_id(service):
    """Traverses Management API to return the first profile id.

    This first queries the Accounts collection to get the first account ID.
    This ID is used to query the Webproperties collection to retrieve the first
    webproperty ID. And both account and webproperty IDs are used to query the
    Profile collection to get the first profile id.

    Args:
      service: The service object built by the Google API Python client library.

    Returns:
      A string with the first profile ID. None if a user does not have any
      accounts, webproperties, or profiles.
    """

    accounts = service.management().accounts().list().execute()

    if accounts.get('items'):
        firstAccountId = accounts.get('items')[0].get('id')
        webproperties = service.management().webproperties().list(
            accountId=firstAccountId).execute()

        if webproperties.get('items'):
            firstWebpropertyId = webproperties.get('items')[0].get('id')
            profiles = service.management().profiles().list(
                accountId=firstAccountId,
                webPropertyId=firstWebpropertyId).execute()

            if profiles.get('items'):
                return profiles.get('items')[0].get('id')

    return None


def get_top_keywords(service, profile_id):
    """Executes and returns data from the Core Reporting API.

    This queries the API for the top 25 organic search terms by visits.

    Args:
      service: The service object built by the Google API Python client library.
      profile_id: String The profile ID from which to retrieve analytics data.

    Returns:
      The response returned from the Core Reporting API.
    """

    return service.data().ga().get(
        ids='ga:' + profile_id,
        start_date='2012-01-01',
        end_date='2012-01-15',
        metrics='ga:visits',
        dimensions='ga:source,ga:keyword',
        sort='-ga:visits',
        filters='ga:medium==organic',
        start_index='1',
        max_results='25').execute()


def print_results(results):
    """Prints out the results.

    This prints out the profile name, the column headers, and all the rows of
    data.

    Args:
      results: The response returned from the Core Reporting API.
    """

    print
    print 'Profile Name: %s' % results.get('profileInfo').get('profileName')
    print

    # Print header.
    output = []
    for header in results.get('columnHeaders'):
        output.append('%30s' % header.get('name'))
    print ''.join(output)

    # Print data table.
    if results.get('rows', []):
        for row in results.get('rows'):
            output = []
            for cell in row:
                output.append('%30s' % cell)
            print ''.join(output)

    else:
        print 'No Rows Found'
