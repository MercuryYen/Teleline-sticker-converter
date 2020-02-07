#coding = unicode
import configparser
from mag import handle_image
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
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					level=logging.INFO)
logger = logging.getLogger(__name__)
config = configparser.ConfigParser()
config.read('config.ini')
app = Flask(__name__)
bot = telegram.Bot(token=(config['TELEGRAM']['ACCESS_TOKEN']))

emojis = "😂😘😍😊😁☺️😔😄😭😒😳😜😉😃😢😝😱😡😏😞😅😚😌😀😋😆😐😕👍👌👿❤️🖤💤🎵🔞"
def random_emoji():
	return emojis[random.randint(0,len(emojis)-1)]





@jit(nopython=True)
def find_sticker_sites(text):
	all_sticker =  [""]
	x = text.find('"mdCMN09Image"')
	print(x)
	while x!=-1:
		#text = text[text[text.find('"mdCMN09Image"'):].find('https'):]
		text = text[text.find('"mdCMN09Image"'):]
		text = text[text.find('https'):]
		add = text[:text.find(';')]
		all_sticker.append(add)
		x = text.find('"mdCMN09Image"')
	return all_sticker[1:]



def find_ex(string,key_string):
	return string[string.find(key_string):]



def start(bot,update):
	bot.sendMessage(chat_id = update.message.chat.id,
						text = "這個Bot可以將Line上的貼圖轉換成telegram上的貼圖，將貼圖商店的網址貼上來就會自動轉換了\n"+
						"This bot can transform Line's stickers to Telegram's sticker. Post line-store's URL to convert.\n\n"+
						"範例example：https://store.line.me/stickershop/product/3962468/ja")

def help_(bot,update):

	bot.sendMessage(chat_id = update.message.chat.id,
					text = "直接傳網址給我就可以惹\nJust send me the URL.\n\n像這個Like this:https://store.line.me/stickershop/product/3962468/ja")
	bot.sendMessage(chat_id = update.message.chat.id,
					text = "如果是有錯誤或問題就找 @Homura343\nWhen in doubt, @Homura343 .")
def about(bot,update):
	bot.sendMessage(chat_id = update.message.chat.id,
						text = "Author:@Homura343\nGithub:https://github.com/Mescury/Teleline-sticker-converter\n")








@app.route('/hook', methods=['POST'])
def webhook_handler():
	if request.method == "POST":
		update = telegram.Update.de_json(request.get_json(force=True), bot)
		dispatcher.process_update(update)
	return 'ok'


def reply_handler(bot, update):

	text = update.message.text

	main_message = bot.sendMessage(chat_id = update.message.chat.id,
						text = "正在試試看這東西\n\nTrying this.").message_id
	print(text)
	try:
		n = requests.get(text)
	except:
		bot.editMessageText(chat_id = update.message.chat.id,
							message_id = main_message,
							text = "無效網址\n\nInvalid URL")
		return
	print(n)
	all_stickers = find_sticker_sites(n.text)
	print(len(all_stickers))
	if len(all_stickers)==0:
		bot.editMessageText(chat_id = update.message.chat.id,
						message_id = main_message,
						text = "沒有找到任何Line貼圖？！\n\nCan't find any line sticker?!")
		return
	temp = text.find("product")
	temp = text[temp+8:]
	sticker_number = temp[:temp.find("/")]

	title = find_ex(find_ex(n.text,"head"),"title")[6:find_ex(find_ex(n.text,"head"),"title")[:].find("LINE")-2]

	#Check if sticker exist
	try:
		a = bot.getStickerSet(name="line"+str(sticker_number)+"_by_RekcitsEnilbot")
		a_len = len(a.stickers)
		status = 1
	except:
		a = 0
		a_len=0
		status = -1
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
	head_sticker=0
	for i in range(a_len,len(all_stickers)):
		z = requests.get(all_stickers[i]).content
		open('temp.png', 'wb').write(z)
		img = Image.open('temp.png').convert('RGBA')
		arr = np.array(img)
		mag=512/max(len(arr[0]),len(arr))
		new_arr = handle_image(mag,arr)
		Image.fromarray(new_arr, 'RGBA').save("output"+str(i)+".png")

		sticker = bot.uploadStickerFile(user_id = update.message.from_user.id,
								png_sticker=open("output"+str(i)+".png", 'rb')).file_id
		if i==0 and status == -1:
			head_sticker = sticker
			bot.createNewStickerSet(user_id=update.message.from_user.id,
									name = "line"+str(sticker_number)+"_by_RekcitsEnilbot",
									title = title+" @RekcitsEnilbot",
									png_sticker = sticker,
									emojis = random_emoji())
		else:
			bot.addStickerToSet(user_id=update.message.from_user.id,
								name = "line"+str(sticker_number)+"_by_RekcitsEnilbot",
								png_sticker = sticker,
								emojis = random_emoji())
		'''bot.sendDocument(chat_id = update.message.chat.id, 
						document = open("output"+str(i)+".png", 'rb'),
						caption = "")'''
		temp_message2 = temp_message
		for j in range(i+1):
			temp_message2 += "￭"
		for j in range(len(all_stickers)-i-1):
			temp_message2 += "_"
		temp_message2 += str(i+1)+"/" + str(len(all_stickers))
		bot.editMessageText(chat_id = update.message.chat.id,
						message_id = main_message,
						text = temp_message2)
	bot.sendMessage(chat_id = update.message.chat.id,
						text = "噠啦～☆\n\nFinished!"+"\n\nLine sticker number:"+str(sticker_number)+"https://t.me/addstickers/"+"line"+str(sticker_number)+"_by_RekcitsEnilbot")
	bot.sendSticker(chat_id = update.message.chat.id,
					sticker = head_sticker,
					reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text = title,url="https://t.me/addstickers/"+"line"+str(sticker_number)+"_by_RekcitsEnilbot")]]))

dispatcher = Dispatcher(bot, None)

dispatcher.add_handler(CommandHandler('start',start))
dispatcher.add_handler(CommandHandler('help',help_))
dispatcher.add_handler(CommandHandler('about',about))
dispatcher.add_handler(MessageHandler(Filters.text, reply_handler))

if __name__ == "__main__":
	app.run(debug=True)












'''

'''