#coding = unicode
import configparser
import requests
from PIL import Image
import numpy as np
from numba import jit
from telegram.ext import Dispatcher, MessageHandler, Filters,CommandHandler
from telegram import InlineKeyboardButton,InlineKeyboardMarkup
import telegram
from flask import Flask,request
import logging
import random
import threading
import json
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					level=logging.INFO)
logger = logging.getLogger(__name__)
config = configparser.ConfigParser()
config.read('config.ini')
app = Flask(__name__)
bot = telegram.Bot(token=(config['TELEGRAM']['ACCESS_TOKEN']))

emojis = "😂😘😍😊😁😔😄😭😒😳😜😉😃😢😝😱😡😏😞😅😚😌😀😋😆😐😕👍👌👿❤🖤💤🎵🔞"

def random_emoji():
	return emojis[random.randint(0,len(emojis)-1)]


def isNum(char):
	return ord('0')<=ord(char) and ord(char) <= ord('9')

def list_of_string_split(list_of_string, split_by):
	output = []
	for i in list_of_string:
		output += i.split(split_by)
	return [i for i in output if i != ""]

def findStickerNumInUrl(string):
	allSplit = list_of_string_split([string], "/")
	allSplit = list_of_string_split(allSplit, "=")
	allSplit = list_of_string_split(allSplit, "?")

	print(allSplit)
	if string.find("sticonshop") == -1:
		for i in allSplit:
			ok = True

			for j in i:
				if not isNum(j):
					ok = False

			if ok and len(i)>0:
				return i

	for i in range(len(allSplit)):
		if allSplit[i] == "sticon":
			return allSplit[i+1]

		if allSplit[i] == "product":
			return allSplit[i+1]

	return -1

def getPack(sticker_number):
	a_len = -1
	a = 0
	try:
		a = bot.getStickerSet(name="line"+str(sticker_number)+"_by_RekcitsEnilbot")
		a_len = len(a.stickers)
	except Exception as e:
		print(e)
		a_len=0

	return a_len, a

def main_handle(sticker_number,chat_id,main_message,all_stickers,title):

	if str(sticker_number) == "-1":
		print("no sticker number")
		bot.editMessageText(chat_id = chat_id,
						message_id = main_message,
						text = "沒有貼圖編號，無法建立貼圖包。\n\nThere isn't any sticker number so I can't create sticker pack.")
		return
	a_len, a = getPack(sticker_number)
	status = 0
	if a_len == 0:
		status = -1
	else:
		status = 1

	head_sticker=0
	temp_message = title+"\n發現"+str(len(all_stickers))+"張貼圖\n\nFound "+str(len(all_stickers))+" stickers\n"
	for i in range(a_len,len(all_stickers)):
		z = requests.get(all_stickers[i]).content
		open('temp'+str(i)+'.png', 'wb').write(z)
		img = Image.open('temp'+str(i)+'.png').convert('RGBA')
		arr = np.array(img)
		mag=512/max(len(arr[0]),len(arr))
		#new_arr = handle_image(mag,arr)
		#Image.fromarray(new_arr, 'RGBA').save("output"+str(i)+".png")

		newY = round(len(arr)*mag)
		newX = round(len(arr[0])*mag)

		if newX>512:
			newX=512
		if newY>512:
			newY=512

		img.resize((newX, newY),Image.ANTIALIAS).save("output"+str(i)+".png")
		sticker = bot.uploadStickerFile(user_id = chat_id,
								png_sticker=open("output"+str(i)+".png", 'rb')).file_id
		rnd_emoji = random_emoji()
		if i==0 and status == -1:
			head_sticker = sticker
			print(sticker_number)
			print("line"+str(sticker_number)+"_by_RekcitsEnilbot")
			try:
				bot.createNewStickerSet(user_id=chat_id,
										name = "line"+str(sticker_number)+"_by_RekcitsEnilbot",
										title = title+" @RekcitsEnilbot",
										png_sticker = sticker,
										emojis = rnd_emoji)
			except Exception as e: 
				print(e)
				return
		else:
			a_len, a = getPack(sticker_number)
			if a_len != i:
				bot.deleteMessage(chat_id = chat_id,
									message_id = main_message)
				# bot.editMessageText(chat_id = chat_id,
				# 					message_id = main_message,
				# 					text = "出了點問題，具體來說是同時有兩個在上傳貼圖\n\nError:Multi thread is not available.")
				return 
			bot.addStickerToSet(user_id=chat_id,
								name = "line"+str(sticker_number)+"_by_RekcitsEnilbot",
								png_sticker = sticker,
								emojis = rnd_emoji)
		'''bot.sendDocument(chat_id = update.message.chat.id, 
						document = open("output"+str(i)+".png", 'rb'),
						caption = "")'''

		temp_message2 = temp_message
		for j in range(i+1):
			temp_message2 += "￭"
		for j in range(len(all_stickers)-i-1):
			temp_message2 += "_"
		temp_message2 += str(i+1)+"/" + str(len(all_stickers))
		try:
			bot.editMessageText(chat_id = chat_id,
						message_id = main_message,
						text = temp_message2)
		except Exception as e: 
			print(e)

	bot.sendMessage(chat_id = chat_id,
						text = "噠啦～☆\n\nFinished!"+"\n\nLine sticker number:"+str(sticker_number)+"\nhttps://t.me/addstickers/line"+str(sticker_number)+"_by_RekcitsEnilbot")
	if head_sticker == 0:
		head_sticker = a.stickers[0].file_id

	bot.sendSticker(chat_id = chat_id,
					sticker = head_sticker,
					reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text = title,url="https://t.me/addstickers/line"+str(sticker_number)+"_by_RekcitsEnilbot")]]))

	return 

def main_handle_for_message_sticker(sticker_number,chat_id,main_message,all_stickers,title):
	if str(sticker_number) == "-1":
		print("no sticker number")
		bot.editMessageText(chat_id = chat_id,
						message_id = main_message,
						text = "沒有貼圖編號，無法建立貼圖包。\n\nThere isn't any sticker number so I can't create sticker pack.")
		return

	a_len, a = getPack(sticker_number)
	status = 0
	if a_len == 0:
		status = -1
	else:
		status = 1

	head_sticker=0
	temp_message = title+"\n發現"+str(len(all_stickers))+"張貼圖\n\nFound "+str(len(all_stickers))+" stickers\n"
	for i in range(a_len,len(all_stickers)):
		z = requests.get(all_stickers[i][0]).content
		open('temp1'+str(i)+'.png', 'wb').write(z)
		img = Image.open('temp1'+str(i)+'.png').convert('RGBA')
		base = np.array(img)

		z = requests.get(all_stickers[i][1]).content
		open('temp2'+str(i)+'.png', 'wb').write(z)
		img = Image.open('temp2'+str(i)+'.png').convert('RGBA')
		text = np.array(img)

		for ii in range(len(base)):
			for jj in range(len(base[ii])):
				power = text[ii][jj][3]/255
				base[ii][jj] = base[ii][jj] * (1-power) + text[ii][jj] * power

		

		mag=512/max(len(base[0]),len(base))
		#new_arr = handle_image(mag,base)
		#Image.fromarray(new_arr, 'RGBA').save("output"+str(i)+".png")
		Image.fromarray(base, 'RGBA').resize((round(len(base[0])*mag), round(len(base)*mag)),Image.ANTIALIAS).save("output"+str(i)+".png")


		sticker = bot.uploadStickerFile(user_id = chat_id,
								png_sticker=open("output"+str(i)+".png", 'rb')).file_id
		rnd_emoji = random_emoji()
		if i==0 and status == -1:
			head_sticker = sticker
			bot.createNewStickerSet(user_id=chat_id,
									name = "line"+str(sticker_number)+"_by_RekcitsEnilbot",
									title = title+" @RekcitsEnilbot",
									png_sticker = sticker,
									emojis = rnd_emoji)
		else:
			a_len, a = getPack(sticker_number)
			if a_len != i:
				bot.deleteMessage(chat_id = chat_id,
									message_id = main_message)
				# bot.editMessageText(chat_id = chat_id,
				# 					message_id = main_message,
				# 					text = "出了點問題，具體來說是同時有兩個在上傳貼圖\n\nError:Multi thread is not available.")
				return 
			bot.addStickerToSet(user_id=chat_id,
								name = "line"+str(sticker_number)+"_by_RekcitsEnilbot",
								png_sticker = sticker,
								emojis = rnd_emoji)
		'''bot.sendDocument(chat_id = update.message.chat.id, 
						document = open("output"+str(i)+".png", 'rb'),
						caption = "")'''

		temp_message2 = temp_message
		for j in range(i+1):
			temp_message2 += "￭"
		for j in range(len(all_stickers)-i-1):
			temp_message2 += "_"
		temp_message2 += str(i+1)+"/" + str(len(all_stickers))
		try:
			bot.editMessageText(chat_id = chat_id,
						message_id = main_message,
						text = temp_message2)
		except Exception as e:
			print(e)

	bot.sendMessage(chat_id = chat_id,
						text = "噠啦～☆\n\nFinished!"+"\n\nLine sticker number:"+str(sticker_number)+"\nhttps://t.me/addstickers/line"+str(sticker_number)+"_by_RekcitsEnilbot")
	if head_sticker == 0:
		head_sticker = a.stickers[0].file_id

	bot.sendSticker(chat_id = chat_id,
					sticker = head_sticker,
					reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text = title,url="https://t.me/addstickers/line"+str(sticker_number)+"_by_RekcitsEnilbot")]]))

	return 



def con_req(sticker_number,chat_id,main_message,all_stickers,title):
	a_len, a = getPack(sticker_number)
	if a_len < len(all_stickers):
		data={
			"sticker_number":sticker_number,
			"chat_id":chat_id,
			"main_message":main_message,
			"all_stickers":json.dumps(all_stickers),
			"title":title
		}
		requests.post("https://rekcits.herokuapp.com/continue",data=data)
		#requests.post("https://06775bc4b6d1.ngrok.io/continue",data=data)

	else:
		return

@jit(nopython=True)
def equalStr(a, b):
	if len(a)!=len(b):
		return False
	for i in range(len(a)):
		if a[i] != b[i]:
			return False
	return True

@jit(nopython=True)
def aIsInb(a, b):
	for i in b:
		if equalStr(a,i):
			return True
	return False

@jit(nopython=True)
def find_sticker_sites(text):
	all_sticker =  [""]
	x = text.find('"mdCMN09Image"')
	while x!=-1:
		#text = text[text[text.find('"mdCMN09Image"'):].find('https'):]
		text = text[text.find('"mdCMN09Image"'):]
		text = text[text.find('https'):]
		add = text[:text.find('.png')+4]
		all_sticker.append(add)
		x = text.find('"mdCMN09Image"')

	if len(all_sticker[1:]) == 0 and text.find('data-default-text') == -1:
		x = text.find('"mdCMN09Image FnCustomBase"')
		while x!=-1:
			#text = text[text[text.find('"mdCMN09Image"'):].find('https'):]
			text = text[text.find('"mdCMN09Image FnCustomBase"'):]
			text = text[text.find('https'):]
			add = text[:text.find('.png')+4]
			all_sticker.append(add)
			x = text.find('"mdCMN09Image FnCustomBase"')
	
	out = []

	for i in all_sticker[1:]:
		if not aIsInb(i, out):
			out.append(i)

	return out


@jit(nopython=True)
def find_message_sticker_sites(text):
	all_sticker =  [[""]]
	x = text.find('"mdCMN09Li FnStickerPreviewItem"')
	while x!=-1:
		#text = text[text[text.find('"mdCMN09Image"'):].find('https'):]
		text = text[text.find('"mdCMN09Li FnStickerPreviewItem"'):]
		
		temp = []
		text = text[text.find('staticUrl'):]
		text = text[text.find('https'):]
		add = text[:text.find('.png')+4]
		temp.append(add)
		text = text[text.find('customOverlayUrl'):]
		text = text[text.find('https'):]
		add = text[:text.find('.png')+4]
		temp.append(add)

		all_sticker.append(temp)
		x = text.find('"mdCMN09Li FnStickerPreviewItem"')

	out = []

	for i in all_sticker[1:]:
		if not aIsInb(i, out):
			out.append(i)

	return out




def find_ex(string,key_string):
	return string[string.find(key_string):]



def start(bot,update):
	try:
		bot.sendMessage(chat_id = update.message.chat.id,
						text = "這個Bot可以將Line上的貼圖轉換成telegram上的貼圖，將貼圖商店的網址貼上來就會自動轉換了\n"+
						"This bot can transform Line's stickers to Telegram's sticker. Post line-store's URL to convert.\n\n"+
						"範例example：https://store.line.me/stickershop/product/3962468/ja")
	except Exception as e:
		print(e)
	

def help_(bot,update):
	try:
		bot.sendMessage(chat_id = update.message.chat.id,
						text = "直接傳網址給我就可以惹\nJust send me the URL.\n\n像這個Like this:https://store.line.me/stickershop/product/3962468/ja")
		bot.sendMessage(chat_id = update.message.chat.id,
						text = "如果是有錯誤或問題就到這\n https://t.me/ArumohChannelGroup\nWhen in doubt, https://t.me/ArumohChannelGroup .")
	except Exception as e:
		print(e)
def about(bot,update):
	try:
		bot.sendMessage(chat_id = update.message.chat.id,
						text="Author:@Homura343\nChannel:https://t.me/ArumohChannel\nChannel Group:https://t.me/ArumohChannelGroup\nGithub:https://github.com/Mescury/Teleline-sticker-converter\n")
	except Exception as e:
		print(e)








@app.route('/hook', methods=['POST'])
def webhook_handler():
	if request.method == "POST":
		update = telegram.Update.de_json(request.get_json(force=True), bot)
		dispatcher.process_update(update)
	return 'ok'


def reply_handler(bot, update):

	text = update.message.text

	try:
		main_message = bot.sendMessage(chat_id = update.message.chat.id,
						text = "正在試試看這東西\n\nTrying this.").message_id
	except Exception as e:
		print(e)
	print(text)
	try:
		n = requests.get(text)
	except Exception as e:
		print(e)
		bot.editMessageText(chat_id = update.message.chat.id,
							message_id = main_message,
							text = "無效網址\n\nInvalid URL")
		return
	#print(n.text)
	all_stickers = find_sticker_sites(n.text)

	if len(all_stickers)!=0:

		print(len(all_stickers))
		if len(all_stickers)>=5:
			print(all_stickers[:5])

		# temp = text.find("product")
		# if temp!=-1:
		# 	temp = text[temp+8:]
		# else:
		# 	temp = text.find("sticker")
		# 	temp = text[temp+8:]
		# sticker_number = temp[:temp.find("/")]
		sticker_number = findStickerNumInUrl(text)
		print(sticker_number)
		#title = find_ex(find_ex(n.text,"head"),"title")[6:find_ex(find_ex(n.text,"head"),"title")[:].find("LINE")-2].replace("&amp;","&")
		title = find_ex(n.text, "sticker-name-title")[20:]
		title = title[:title.find("</p>")]
		print(title)

		#Check if sticker exist
		a_len, a = getPack(sticker_number)
		status = 0
		if a_len == 0:
			status = -1
		else:
			status = 1


		if status == 1:
			if len(a.stickers) != len(all_stickers):
				bot.editMessageText(chat_id = update.message.chat.id,
									message_id = main_message,
									text = "貼圖包更新\n\nUpdate the sticker set.")
			else:
				bot.editMessageText(chat_id = update.message.chat.id,
									message_id = main_message,
									text = "總算找到了\nThis one?!"+"\n\nLine sticker number:"+str(sticker_number))

				bot.sendSticker(chat_id = update.message.chat.id,
							sticker = a.stickers[0].file_id,
							reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text = title,url="https://t.me/addstickers/"+"line"+str(sticker_number)+"_by_RekcitsEnilbot")]]))
				return

		temp_message = title+"\n發現"+str(len(all_stickers))+"張貼圖\n\nFound "+str(len(all_stickers))+" stickers\n"
		temp_message2 = temp_message
		for i in range(len(all_stickers)):
			temp_message2 += "_"
		temp_message2 += "0/" + str(len(all_stickers))
		bot.editMessageText(chat_id = update.message.chat.id,
							message_id = main_message,
							text = temp_message2)


		main_handle(sticker_number,update.message.chat.id,main_message,all_stickers,title)

	else:

		all_stickers = find_message_sticker_sites(n.text)
		#print(n.text)

		print(len(all_stickers))
		if len(all_stickers)==0:
			bot.editMessageText(chat_id = update.message.chat.id,
							message_id = main_message,
							text = "沒有找到任何Line貼圖？！\n\nCan't find any line sticker?!")
			return

		sticker_number = findStickerNumInUrl(text)

		print(sticker_number)

		#title = find_ex(find_ex(n.text,"head"),"title")[6:find_ex(find_ex(n.text,"head"),"title")[:].find("LINE")-2].replace("&amp;","&")
		title = find_ex(n.text, "sticker-name-title")[20:]
		title = title[:title.find("</p>")]
		print(title)

		#Check if sticker exist
		a_len, a = getPack(sticker_number)
		status = 0
		if a_len == 0:
			status = -1
		else:
			status = 1

		if status == 1:
			if len(a.stickers) != len(all_stickers):
				bot.editMessageText(chat_id = update.message.chat.id,
									message_id = main_message,
									text = "貼圖包更新\n\nUpdate the sticker set.")
			else:
				bot.editMessageText(chat_id = update.message.chat.id,
									message_id = main_message,
									text = "總算找到了\nThis one?!"+"\n\nLine sticker number:"+str(sticker_number))

				bot.sendSticker(chat_id = update.message.chat.id,
							sticker = a.stickers[0].file_id,
							reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text = title,url="https://t.me/addstickers/"+"line"+str(sticker_number)+"_by_RekcitsEnilbot")]]))
				return

		temp_message = title+"\n發現"+str(len(all_stickers))+"張貼圖\n\nFound "+str(len(all_stickers))+" stickers\n"
		temp_message2 = temp_message
		for i in range(len(all_stickers)):
			temp_message2 += "_"
		temp_message2 += "0/" + str(len(all_stickers))
		bot.editMessageText(chat_id = update.message.chat.id,
							message_id = main_message,
							text = temp_message2)


		main_handle_for_message_sticker(sticker_number,update.message.chat.id,main_message,all_stickers,title)
	

dispatcher = Dispatcher(bot, None)

dispatcher.add_handler(CommandHandler('start',start))
dispatcher.add_handler(CommandHandler('help',help_))
dispatcher.add_handler(CommandHandler('about',about))
dispatcher.add_handler(MessageHandler(Filters.text, reply_handler))

if __name__ == "__main__":
	app.run(debug=True)
