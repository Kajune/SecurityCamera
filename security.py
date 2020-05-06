import cv2
import numpy as np
import smtplib
import datetime

from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

import mimetypes

thresh = 0.3
refUpdate = 60
coolingTime = 600

address = 'surveillancecameraapp@gmail.com'
password = 'surveillance'
notifyAddress = 'ryuzoji21@gmail.com'

def create_message(from_addr, to_addr, subject, body, attach_files):
	"""
	Mailのメッセージを構築する
	"""
	msg = MIMEMultipart()
	msg["Subject"] = subject
	msg["From"] = from_addr
	msg["To"] = to_addr


	body = MIMEText(body)
	msg.attach(body)

	for attach_file in attach_files:
		mimetype, mimeencoding = mimetypes.guess_type(attach_file['path'])
		if mimeencoding or (mimetype is None):
			mimetype = 'application/octet-stream'
		maintype, subtype = mimetype.split('/')
		attachment = MIMEBase(maintype, subtype)

		file = open(attach_file['path'], 'rb')
		attachment.set_payload(file.read())
		file.close()
		encoders.encode_base64(attachment)
		msg.attach(attachment)
		attachment.add_header("Content-Dispositon", "attachment", filename=attach_file['name'])

	return msg

def sendMail(normal, abnormal):	
	body = "不審なアクティビティを検出しました。時刻: " + str(datetime.datetime.now())

	cv2.imwrite('normal.jpg', normal)
	cv2.imwrite('abnormal.jpg', abnormal)

	attach_files = [
		{'name':'normal.jpg', 'path':'normal.jpg'},
		{'name':'abnormal.jpg', 'path':'abnormal.jpg'}
	]

	msg = create_message(address, notifyAddress, 
		'Suspicious activity detected', body, attach_files)
	
	smtpobj = smtplib.SMTP('smtp.gmail.com', 587)
	smtpobj.ehlo()
	smtpobj.starttls()
	smtpobj.ehlo()
	smtpobj.login(address, password)
	smtpobj.send_message(msg)
	smtpobj.quit()

if __name__ == '__main__':
	cap = cv2.VideoCapture(0)

	fourcc = cv2.VideoWriter_fourcc(*'XVID')
	record = cv2.VideoWriter('recordVideo.mp4', fourcc, cap.get(cv2.CAP_PROP_FPS), 
		(int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))

	_, refFrame = cap.read()
	refFrame = refFrame.astype(np.float32) / 255

	count = 0
	activity = False
	cool = 0

	while True:
		ret, frame = cap.read()
		frame = frame.astype(np.float32) / 255
		vis = frame.copy()

		if ret:
			diff = np.max(np.abs(frame - refFrame), axis=2)
			diff[diff > thresh] = 1
			diff[diff < 1] = 0

			kernel = np.ones((3,3), np.uint8)
			diff = cv2.morphologyEx(diff, cv2.MORPH_OPEN, kernel)

			vis[:,:,2][diff > 0] = 1
			indices = np.where(diff > 0)
			if indices[0].shape[0] > 0:
				# 異常あり

				if not activity:
					activity = True
					cool = coolingTime
					sendMail(refFrame * 255, frame * 255)

				record.write((vis * 255).astype(np.uint8))

				vis = cv2.rectangle(vis, (np.min(indices[1]), np.min(indices[0])), (np.max(indices[1]), np.max(indices[0])), (0,255,0), 3)
			else:
				if cool <= 0:
					activity = False
				else:
					cool -= 1

			if count % refUpdate == 0:
				refFrame = frame
		else:
			print('Camera capture failed.')
			break

		cv2.imshow('', vis)
		k = cv2.waitKey(1) & 0xff

		if k == ord('q'):
			break

		count += 1
