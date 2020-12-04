# -*- coding: euc-kr -*-
import urllib.request
import urllib.parse
import json
import csv
import smtplib
from email.mime.text import MIMEText
import textile
import sys
from datetime import datetime
import os

def load_config():
	try:
		global client_id
		global client_secret
		global display
		global sort
		global item_list_file
		global email_sender
		global admin_email
		global app_passwd
		global log_dir
		admin_email = ""
		with open('config.txt', 'r', encoding='euc-kr') as f:
			json_data = json.load(f)
			client_id = json_data["client_id"]
			client_secret = json_data["client_secret"]
			display = json_data["display"]
			sort = json_data["sort"]
			item_list_file = json_data["item_list_file"]
			email_sender = json_data["email_sender"]
			admin_email = json_data["admin_email"]
			app_passwd = json_data["app_passwd"]
			log_dir = json_data["log_dir"]
	except Exception as e:
		print(e)
		return False
	return True

def request_query(client_id, client_secret, query):
	url="https://openapi.naver.com/v1/search/shop.json"
	option="&display="+str(display)+"&start=1&sort="+sort
	url_query = url + "?query=" + urllib.parse.quote(query) + option

	request = urllib.request.Request(url_query)
	request.add_header("X-Naver-Client-Id", client_id)
	request.add_header("X-Naver-Client-Secret", client_secret)

	response = urllib.request.urlopen(request)
	rescode = response.getcode()
	if (rescode == 200):
		response_body = response.read()
		return response_body.decode('utf-8')
	else:
		return "Error code:"+response

def makeTextile(title, link, lprice, mallName):
	result  = "* 제품명 : " + title + "\n"
	result += '* 링크 : "' + link + '":' + link + '\n'
	result += "* 최저가 : " + ("{:,}".format(int(lprice))) + " 원\n"
	result += "* 쇼핑몰 : " + mallName + "\n"
	return result 

def parse_response(response, min_lprice, max_lprice):
	json_data = json.loads(response)

	json_items = json_data["items"]

	result = ""

	for item in json_items:
		if int(item["lprice"]) > int(min_lprice) and int(item["lprice"]) < int(max_lprice):
			#result += "제품명\t: " + item["title"] + "\n링크\t: " + item["link"] + "\n최저가\t: " + item["lprice"] + "\n쇼핑몰\t: " + item["mallName"] + "\n\n"
			result += makeTextile(item["title"], item["link"], item["lprice"], item["mallName"]) + '\n<br />\n'
			# print("제품명\t: " + item["title"])
			# print("링크\t: " + item["link"])
			# print("최저가\t: " + item["lprice"])
			# print("쇼핑몰\t: " + item["mallName"])
			# print("")
			#print(item)
	return result

def load_item_list():
	items = []
	with open(item_list_file, 'r', encoding='euc-kr') as f:
		rdr = csv.reader(f)
		next(rdr)
		i = 0
		for line in rdr:
			if line[0] == '1':
				items.append(line)
#				print (items)
	return items

def sendmail(addr, contents, title):
	# 세션 생성
	s = smtplib.SMTP('smtp.gmail.com', 587)

	# TLS 보안 시작
	s.starttls()

	# 로그인 인증
	s.login(email_sender, app_passwd)

	# 보낼 메시지 설정
	html = "<html><head></head><body>" + textile.textile(contents) + "</p></body></html>"
	msg = MIMEText(html, 'html')
	msg['Subject'] = title

	# 메일 보내기
	try:
		s.sendmail(email_sender, addr, msg.as_string())
	except Exception as err:
		print(err)

	# 세션 종료
	s.quit()


#resp = request_query(client_id, client_secret, "c316bee")
#print (request_query(client_id, client_secret, "c316bee"))
#print (request_query(client_id, client_secret, "audio%20pl300"))
#parse_response(resp, 300000, 400000)
#print (load_item_list())

if __name__ == "__main__":	
	summary_log = ""
	err_log = ""
	parse_count = 0
	err_count = 0
	items = []

	now = datetime.now()
	date_time = now.strftime("%Y/%m/%d, %H:%M:%S")
	summary_log += "\n\n작업 시작: " + date_time + "\n\n"

	if True == load_config():
		if 0 == len(log_dir):
			log_dir = '.'
		if False == os.path.isdir(log_dir):
			os.mkdir(log_dir)
		log_file = log_dir + "\\" + now.strftime("%Y%m%d_%H%M%S") + ".txt"
		sys.stdout = open(log_file, 'w')
		items = load_item_list()
		for item in items:
			print (item)
			try:
				resp = request_query(client_id, client_secret, item[3])
				parsed = parse_response(resp, item[1], item[2])
				if len(parsed) != 0:
					parse_count += 1
					print (parsed + "메일을 " + item[4] +" 주소로 보냅니다.\n")
					sendmail(item[4], parsed + "\n", '제품명 : [' + item[3] + '] 가격 정보')
			except Exception as err:
				err_count += 1
				print(err)
	else:
		err_log += "config.txt를 로드하는 중에 실패 하였습니다.\n"

	if 0 != len(err_log):
		summary_log += err_log + "\n"
	else:
		summary_log += "총 제품 수 : " + str(len(items)) + "\n"
		summary_log += "조건 부합 제품 수 : " + str(parse_count) + "\n"
		summary_log += "에러 발생 제품 수 : " + str(err_count) + "\n"
	
	date_time = now.strftime("%Y/%m/%d, %H:%M:%S")
	summary_log += "\n\n작업 완료: " + date_time + "\n\n"
	print(summary_log)

	try:
		admin_email
		if 0 != len(admin_email):
			print ("관리자("+ admin_email +")에게 작업 로그를 보냅니다.\n")
			sendmail(admin_email, summary_log, "관리자 로그 - " + sys.argv[0])
		else:
			print ("관리자 메일이 지정되어 있지 않습니다. config.txt를 확인해 주십시오.\n")
	except NameError:
		print ("관리자 메일이 지정되어 있지 않습니다. config.txt를 확인해 주십시오.\n")
