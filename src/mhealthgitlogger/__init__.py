import gitlogger
import iso8601
import json
import requests
import sys

HELP_MESSAGE = '''
mhealthgitlogger [action] [options]
	actions and their options
		help			Prints this message.
		push_updates	Pushes gitlogger updates to mHealth.
			username	GitHub username configured with gitlogger
			oauth_token	Token for mHealth APi
'''

class Usage(Exception):
	def __init__(self, msg):
		super(Usage, self).__init__(msg)
		self.msg = msg

def help_msg():
	print >> sys.stderr, HELP_MESSAGE

class mHealthClient(object):
	def __init__(self, oauth_token):
		self.oauth_token = oauth_token
	def get_records(self, min_date=None, max_date=None):
		url = 'https://api-mhealth.att.com/v2/health/source/gitlogger/data'
		payload = {'oauth_token':self.oauth_token}
		if min_date:
			payload['from'] = min_date
		if max_date:
			payload['to'] = max_date
		request = requests.get(url, params=payload)
		print "text", request.text
		result = json.loads(request.text)
		print "result", result
		return result
	
	def post_record(self, record):
		url = 'https://api-mhealth.att.com/v2/health/source/gitlogger/data'
		payload = [record,]
		headers = {'content-type': 'application/json', 'authorization':"OAuth %s" % self.oauth_token}
		request = requests.post(url, data=json.dumps(payload), headers=headers)
		
	
def push_commits(commits, oauth_token):
	min_date = None
	max_date = None
	min_date_original = None
	max_date_original = None
	unsubmitted_records = []
	for d in commits.keys():
		parsed_date = iso8601.parse_date(d)
		if min_date is None:
			min_date = parsed_date
			max_date = parsed_date
		if parsed_date > max_date:
			max_date = parsed_date
			max_date_original = d
		if parsed_date < min_date:
			min_date = parsed_date
			min_date_original = d
		unsubmitted_records.append({'timestamp':d, 'name':'changed_lines', 'value':commits[d]['added']+commits[d]['removed']})
	print "Min date:", min_date_original
	print "Max date:", max_date_original
	client = mHealthClient(oauth_token)
	records = client.get_records(min_date=min_date_original, max_date=max_date_original)
	submitted_records = []
	for record in records:
		submitted_records.append(iso8601.parse_date(record['timestamp']))
	records_to_send = []	
	for unsubmitted_record in unsubmitted_records:
		exists = False
		d = iso8601.parse_date(unsubmitted_record['timestamp'])
		for submitted_record in submitted_records:
			if d == submitted_record:
				exists = True
				break
		if not exists:
			records_to_send.append(unsubmitted_record)
	print "records_to_send count:", len(records_to_send)
	for unsubmitted_record in records_to_send:
		print unsubmitted_record
		client.post_record(unsubmitted_record)
	

def main():
	argv = sys.argv
	try:
		if len(argv) < 2:
			raise Usage("No action given.")
		action = argv[1]
		if action == "help":
			help_msg()
		elif action == "push_updates":
			username = argv[2]
			oauth_token = argv[3]
			logger = gitlogger.Gitlogger()
			#logger.checkout_repositories_for_user(username)
			commits = logger.commits_for_user(username)
			push_commits(commits, oauth_token)
		else:
			raise Usage("Unknown action given: %s" % action)
	except Usage as err:
		print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
		print >> sys.stderr, "\t for help use help action"
		print >> sys.stderr, HELP_MESSAGE
		return 2
