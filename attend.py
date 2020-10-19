import os,sys,requests,json,getpass

canvasSubDomain = ""

canvasSamlUrl = ""


class QwicklyHandler(object):
	def __init__(self):
		self.session = requests.Session();
		
		self.sessionAuthorized = False
		
		self.userid = "00000"
		self.loggedIn = False
		
		self.classesByID = {}
		
		self.canvasLoginUrl = "https://{0}.instructure.com/login".format(canvasSubDomain)
		self.samlUrl = canvasSamlUrl
		self.samlLoginUrl = "https://{0}.instructure.com/login/saml".format(canvasSubDomain)
		self.qwicklyExtUrl = "https://"+canvasSubDomain+".instructure.com/courses/{0}/external_tools/9886?display=borderless"
		self.qwicklyUrl = "https://www.qwickly.tools/attendance/takerecord/?request_lms=canvas&id={0}&domain="+canvasSubDomain+".instructure.com&initial_request='initial'&initial_user_id={1}"
		self.oauthUrl = "https://{0}.instructure.com/login/oauth2/accept".format(canvasSubDomain)
		
	def get_class_name_by_id(self,classid):
		if classid not in self.classesByID.keys():
			print("Class {0} not found".format(classid))
			return
		return self.classesByID[classid]
		
	def canvas_login(self):
		loginPage = self.session.get(self.canvasLoginUrl)
		
		# print("jsession" in str(x.content))

		#get saml url and session id from login page
		content = str(loginPage.content)
		samlSessionUrl = self.samlUrl+content.split('action="')[1].split('" method=')[0]

		username = input("Username: ")
		password = getpass.getpass("Password: ")

		loginData = {
						"j_username":username,
						"j_password":password,
						"_eventId_proceed":""
						}

		#query saml page for authentication
		samlResponsePage = self.session.post(samlSessionUrl,data=loginData)

		# print("SAMLResponse" in str(x.content));
		# print(x.content)

		content = str(samlResponsePage.content)

		if "try again" in content:
			print("Invalid credentials")
			input("Press enter to close...")
			exit()
		else:
			None
			# print("Login successful")

		#get saml response
		samlResponse = content.split('value="')[1].split('"/>')[0]

		data = {"SAMLResponse":samlResponse}

		#send saml response to canvas 
		canvasPage = self.session.post(self.samlLoginUrl,data=data)
		content = str(canvasPage.content)
		
		self.userid = content.split("context-user_")[1].split(" responsive")[0]
		print()
		print("User-id: ", self.userid)
		print()
		
		self.loggedIn = True
		
		infoJson = content.split("ENV = ")[1].split("</script>")[0][:-5]
				
		studentInfo = json.loads(infoJson)
		
		f = open("student_info.json","w+")
		f.write(infoJson)
		f.close()
		
		print("Enrolled classes (some may be old or invalid):")
		
		for enrolledClass in studentInfo["STUDENT_PLANNER_COURSES"]:
			print(enrolledClass["id"],enrolledClass["originalName"])
			self.classesByID.update({enrolledClass["id"]:enrolledClass["originalName"]})
			
		print("---")
		print()

	def checkin_for_class(self,classid): 

		# print("Attempting check-in for class "+classid)
	
		if self.loggedIn == False:
			print("Error (checkin_for_class(classid)): Not logged in to canvas")
			return False

		# classid = input("Class id (xxxxx.instructure.com/courses/xxxxx): ")

		#qwickly redirect link
		extUrl = self.qwicklyExtUrl.format(classid)

		#get csrf token
		x = self.session.get(extUrl)

		#if response has valid html response code
		if x:
			# print("good")
			None
		else:
			print("Class with id \""+classid+"\" not found, aborting")
			return

		qwicklyUrl = self.qwicklyUrl.format(classid,self.userid)

		if self.sessionAuthorized == False:

			headers = {"Referer":extUrl}
			qwicklyAuthPage = self.session.get(qwicklyUrl,headers=headers)
			#we are using a new session every time, so we need to reauthorize
			content = str(qwicklyAuthPage.content)

			oauthToken = content.split('"authenticity_token" value="')[1].split('" />')[0]

			data = {
							"utf-8":True,
							"authenticity_token":oauthToken
						}

			#allow qwickly to access your canvas account
			self.session.post(self.oauthUrl,data=data)

			self.sessionAuthorized = True

		headers = {"Referer":extUrl}

		qwicklyPage = self.session.get(qwicklyUrl,headers=headers)

		content = str(qwicklyPage.content)

		middlewareToken = content.split('<input type="hidden" name="csrfmiddlewaretoken" value="')[1].split('">')[0]

		data = {
						"check_in_id":"",
						"student_check_in": "Check In",
						"check_in_remaining_seconds":"1060.0",
						"check_in_session_start":"2021-10-14 15:56:58+00:00",
						"csrfmiddlewaretoken":middlewareToken,
					}

		headers = {"Referer":qwicklyUrl}

		checkinAttempt = self.session.post(qwicklyUrl,headers=headers,data=data)

		content = str(checkinAttempt.content)
		
		f = open("qwickly_page.html","w+")
		f.write(content)
		f.close()

		try:
			className = content.split('<div class="title subHeader bold" title="">')[1].split('</div')[0]
		except:
			print("Error checking in for for class {0} ({1})".format(self.get_class_name_by_id(classid),classid))
			return

		if "Successful" in content:
			print("Check-in successful for class {0} ({1})".format(self.get_class_name_by_id(classid),classid))
		else:
			print("No check-in currently available for class {0} ({1})".format(self.get_class_name_by_id(classid),classid))

handler = QwicklyHandler()
handler.canvas_login()

classes = [84394,82654,81649,85169]
for id in classes:
	handler.checkin_for_class(str(id))
	
input("Press enter to close...")