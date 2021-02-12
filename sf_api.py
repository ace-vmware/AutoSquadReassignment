#! python3

import datetime
import logging
import re
import requests
import slack_api
import os

from simple_salesforce import Salesforce

# SF login
sf = Salesforce(
    username=os.environ["sf_username"],
    password=os.environ["sf_password"],
    security_token=os.environ["SECURITY_TOKEN"])

# Easy method for SalesForce API calls
def sf_api_get(uri):
    url = 'https://vmware-gs.my.salesforce.com' + uri
    headers = sf.headers

    res = requests.get(url, headers=headers)
    content = res.content

    return content


def sf_api_patch(case_id, approvedeny, from_squad, to_squad):
    response = sf.CaseComment.create({
        'ParentID': f'{case_id}',
        'CommentBody': f"Reassignment from {from_squad} to {to_squad} has been {approvedeny}."})

    return response


# Squad Details
SQUAD_OWNER_IDS = {"federal": '00Gf4000002djYA', 'windows': '123', "apple": '12345', "android": '12345',
                   "auth": '12345', "mcm": '12345', "mem": '12345', "mdm": '12345', "mam": '12345'}


def reassign_case_owner(case_id, to_squad):
    if to_squad.lower().strip(' ') in SQUAD_OWNER_IDS:
        sf.Case.update(case_id, {'ownerID': SQUAD_OWNER_IDS[to_squad.lower().strip(' ')]})

class SalesForceCase:
    def __init__(self, case_id):
        self.allAttributes = sf.Case.get(f'{case_id}')
        self.case_number = self.allAttributes.get('CaseNumber')
        self.case_link = ''.join(['https://vmware-gs.lightning.force.com/lightning/r/Case/', f'{case_id}', '/view'])
        self.first_response_met = self.allAttributes.get('GSS_First_Resp_Met__c')
        self.support_group = self.allAttributes.get('GSS_Center__c')
        self.priority = self.allAttributes.get('Priority')
        self.tse_reassigning = self.allAttributes.get('Case_Owner_Name__c')
        self.case_age_delta = (datetime.datetime.now(tz=datetime.timezone.utc) - datetime.datetime.strptime(
            self.allAttributes.get('CreatedDate'), '%Y-%m-%dT%H:%M:%S.%f%z'))
        self.case_age_days = self.case_age_delta.days
        self.case_age_hours = int(round((self.case_age_delta.seconds / 60) / 60, 0))
        self.case_age = f"{self.case_age_days} Day(s), {self.case_age_hours} Hour(s)"


class SalesForceCaseComment:
    def __init__(self, Id):
        self.allAttributes = sf.CaseComment.get(f'{Id}')
        self.CommentBody = self.allAttributes['CommentBody']
        self.ParentId = self.allAttributes['ParentId']
        self.CreatedDate = self.allAttributes['CreatedDate']
        try:
            self.to_squad = (re.compile(r'(?<=To Squad:)\s*\w+').search(self.CommentBody).group()).strip(' ')
            self.from_squad = (re.compile(r'(?<=From Squad:)\s*\w+').search(self.CommentBody).group()).strip(' ')
        except AttributeError as e:
            logging.debug("No squad found: " + str(e))
            self.to_squad = 'None'
            self.from_squad = 'None'

    @classmethod
    def get_reassignment_macro_cases(cls, minutes):
        last_30_minutes = (
                (datetime.datetime.now()
                 + datetime.timedelta(hours=4))
                - datetime.timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        try:
            queryResults = (sf.query_all(
                "SELECT Id "
                "FROM CaseComment "
                f"WHERE CreatedDate >= {last_30_minutes} "
                "AND CommentBody LIKE '%This macro is to be used by support TSE for reassigning tickets%'"))['records']

            caseIds = [case['Id'] for case in queryResults]

            return caseIds

        except Exception as EXCEPTION:
            logging.debug(EXCEPTION)


def slackPost(minutes):
    caseIds = SalesForceCaseComment.get_reassignment_macro_cases(minutes)
    logging.debug("Ids found: " + str(caseIds))
    for Id in caseIds:
        tempCaseComment = SalesForceCaseComment(Id)
        tempCase = SalesForceCase(tempCaseComment.ParentId)

        slack_api.sendBlock(slack_api.slack_client, tempCase.case_link, tempCase.case_number,
                            tempCaseComment.from_squad, tempCaseComment.to_squad, tempCase.tse_reassigning,
                            tempCase.priority, tempCase.support_group, tempCase.first_response_met,
                            tempCase.case_age)

def get_tse_macro_id(case_id):
    macro_id = sf.query(
        "SELECT CommentBody,Id,ParentId "
        "FROM CaseComment "
        f"WHERE ParentId = '{case_id}' "
        "AND CommentBody LIKE '%This macro is to be used by support TSE for reassigning tickets.%'"
    ).get('records')[0].get('Id')

    return macro_id
