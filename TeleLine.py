#coding=utf8
from telegram import InlineKeyboardButton,InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, Dispatcher, CommandHandler, MessageHandler, Filters
from telegram.error import BadRequest
import telegram

import requests

from bs4 import BeautifulSoup

from io import BytesIO
from PIL import Image

import numpy as np

import os

import random

from rq import Queue
from worker import conn

q = Queue(connection=conn)

emojis = "😂😘😍😊😁😔😄😭😒😳😜😉😃😢😝😱😡😏😞😅😚😌😀😋😆😐😕👍👌👿❤🖤💤🎵🔞"
# get a random emoji from emojis
def get_random_emoji():
	return emojis[random.randint(0,len(emojis)-1)]

# split a list of string and automatically remove null string
# ["a12", "1a2"], "a" -> ["12", "1", "2"]
def split_list_of_string_by(list_of_string, split_by):
	output = []
	# split string in list
	for i in list_of_string:
		output += i.split(split_by)

	# remove null string
	return [i for i in output if i != ""]

# extract sticker number from url
# if sticker number is found, return sticker number
# else return null string
# "https://store.line.me/stickershop/product/3962468/ja" -> "3962468"
def get_sticker_number_from_url(url):
	# split url into several independent string by common characters
	allSplit = split_list_of_string_by([url], "/")
	allSplit = split_list_of_string_by(allSplit, "=")
	allSplit = split_list_of_string_by(allSplit, "?")
	allSplit = split_list_of_string_by(allSplit, "&")

	print(allSplit)

	# get sticker number by common url pattern
	for idx, string in enumerate(allSplit):
		if string == "sticker" or string == "product" or string == "id":
			return allSplit[idx + 1]

	# if not found
	return ""

'''
types of sticker (with example):
Normal Stickers: 		https://store.line.me/stickershop/product/3962468/ja
Effect Stickers: 		https://store.line.me/stickershop/product/18082/en
Message Stickers: 		https://store.line.me/stickershop/product/17092/en
Custom Stickers: 		https://store.line.me/stickershop/product/14458/en
Big Stickers: 		 	https://store.line.me/stickershop/product/24202/en
Pop-up Stickers: 		https://store.line.me/stickershop/product/24206/en
With voice or sound:	https://store.line.me/stickershop/product/17050/en
Animated Stickers: 		https://store.line.me/stickershop/product/8549/en
Music Stickers: 		https://store.line.me/stickershop/product/17891/en
'''

'''
get info of sticker
like is_message_sticker, title, image urls

when is_message_sticker is False, 
	urls is a list of sting
when is_message_sticker is True, 
	urls is a list of list of string standing for pairs of images (background image and text image)
'''
def get_sticker_info(text):
	# convert to soup
	soup = BeautifulSoup(text, "html.parser")
	
	# output
	is_message_sticker = False
	title = ""
	urls = []

	# check if it is a typical sticker url and return result
	try:
		# message stickers
		if text.find("data-default-text") != -1:
			classes = soup.find_all("li", "mdCMN09Li FnStickerPreviewItem")
			texts = [c["data-preview"] for c in classes]
			for t in texts:
				urls.append([i[i.find("http"):i.find(".png")+4] for i in t.split("customOverlayUrl")])
			is_message_sticker = True

		# custom stickers
		elif text.find("mdCMN09Image FnCustomBase") != -1:
			classes = soup.find_all("span", "mdCMN09Image FnCustomBase")
			text = [t["style"] for t in classes]
			urls = [t[t.find("(")+1:t.find(";")] for t in text]
			urls = list(dict.fromkeys(urls))
			is_message_sticker = False

		# other normal stickers
		else:
			classes = soup.find_all("span", "mdCMN09Image")
			text = [t["style"] for t in classes]
			urls = [t[t.find("(")+1:t.find(";")] for t in text]
			urls = list(dict.fromkeys(urls))
			is_message_sticker = False
		
		c = soup.find("p", "mdCMN38Item01Ttl")
		title = c.text
	except Exception as e:
		print(e)
		is_message_sticker = False
		title = ""
		urls = []

	if not is_message_sticker and len(urls) > 0:
		for idx in range(len(urls)):
			urls[idx] = urls[idx].replace(")", "")

	return is_message_sticker, title, urls

# get sticker name from sticker number
def get_sticker_name_from_sticker_number(bot, sticker_number):
	return f"line{sticker_number}_by_{bot.username}"

# get telegram sticker set based on name of sticker
def get_sticker_set(bot, sticker_name):
	
	result = None
	try:
		result = bot.get_sticker_set(name=sticker_name)
	except:
		result = None

	return result

# delete all stickers from sticker set to delete a sticker set
def delete_sticker_set(bot, sticker_set):
	for sticker in sticker_set.stickers:
		bot.delete_sticker_from_set(sticker.file_id)

# get image from image url
# download and convert to image format
def get_image_from_url(url):
	return Image.open(BytesIO(requests.get(url).content)).convert('RGBA')

# merge two images with repect to transparency
def merge_image(background_image, text_image):
	background = np.array(background_image)
	text = np.array(text_image)
	output = np.array(text_image)

	for y in range(len(background)):
		for x in range(len(background[y])):
			power = text[y][x][3]/255
			output[y][x] = background[y][x] * (1-power) + text[y][x] * power

	return Image.fromarray(output, 'RGBA')

# resize image to have the max dimension be a specific number
# 5x10, 20 -> 10x20
# 10x20, 5 -> 3x5 where 3 standing for round(2.5)
def resize_image_with_maximum(image, maximum):
	w, h = image.size
	proportion = 512 / max(w,h)

	new_w = round(w * proportion)
	new_h = round(h * proportion)
	if new_w >= new_h: new_w = 512
	if new_h >= new_w: new_h = 512

	return image.resize((new_w, new_h), Image.BICUBIC)

# get image with telegram sticker format from image url 
# when is_message_sticker = False, url should be a image url
# when is_message_sticker = True, url should be a tuple of image urls

# step:
# 1. download image
# (1.5. if is_message_sticker = true, merge images)
# 2. resize to ??? x 512 or 512 x ??? (where ??? <= 512)
def get_sticker_image_from_url(is_message_sticker, url):
	# get image from url
	if not is_message_sticker:
		image = get_image_from_url(url)
	else:
		background_image = get_image_from_url(url[0])
		text_image = get_image_from_url(url[1])
		image = merge_image(background_image, text_image)

	image = resize_image_with_maximum(image, 512)
	return image

# main procession of text
# get page from text, extract sticker's image urls, download image, resize image, upload image
def process_text(access_token, user_id, text, output_message_id):

	bot = telegram.Bot(token=access_token)

	# check if text is valid
	try:
		# check if there is a sticker number in text 
		sticker_number = get_sticker_number_from_url(text)
		if sticker_number == "":
			raise Exception("Can't find any sticker number in text")
		
		# check if text is an url
		n = requests.get(text)

	except Exception as e:
		print(e)
		bot.edit_message_text(	chat_id = user_id,
								message_id = output_message_id,
								text = ("無效網址\n\n"
										"Invalid URL"))
		return
				
	is_message_sticker, title, urls = get_sticker_info(n.text)

	# can't find any sticker
	if len(urls) == 0:
		bot.edit_message_text(chat_id = user_id,
							message_id = output_message_id,
							text = 	("沒有找到任何Line貼圖？！\n\n"
									"Can't find any line sticker?!"))
		return

	sticker_name = get_sticker_name_from_sticker_number(bot, sticker_number)

	has_uploaded_first_image = False
	
	backup_count = 0
	new_sticker_name = sticker_name[:]
	is_valid_sticker_number = False	
	while not is_valid_sticker_number:

		print(new_sticker_name)

		# check if there has been a sticker set
		sticker_set = get_sticker_set(bot, new_sticker_name)

		# three conditions:
		# 1. no sticker set -> upload stickers
		# 2. exist sticker set, and sticker set finished uploading -> return finished sticker set
		# 3. exist sticker set, but sticker set didn't finish uploading -> delete old sticker set and upload stickers
		if sticker_set != None:
			# condition 2
			if len(sticker_set.stickers) == len(urls):
				bot.edit_message_text(	chat_id = user_id,
										message_id = output_message_id,
										text = (	f"總算找到了\n"
													f"This one?!\n\n"
													f"Line sticker number:{sticker_number}"))

				bot.send_sticker(	chat_id = user_id,
									sticker = sticker_set.stickers[0].file_id,
									reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(	text = title, 
																								url = f"https://t.me/addstickers/{new_sticker_name}")]]))
				return
			# condition 3
			else:
				delete_sticker_set(bot, sticker_set)

		# upload
		upload_static_text = (	f"{title}\n"
								f"發現{len(urls)}張貼圖\n\n"
								f"Found {len(urls)} stickers\n")

		# first image for creating a sticker set
		if not has_uploaded_first_image:
			try:
				sticker_image = get_sticker_image_from_url(is_message_sticker, urls[0])
			except Exception as e:
				print(e)


			sticker_image.save(f"{sticker_number}.png")
			sticker0 = bot.upload_sticker_file(	user_id = user_id,
												png_sticker=open(f"{sticker_number}.png", 'rb')).file_id
			has_uploaded_first_image = True

		# create a sticker set
		is_potential_valid_sticker_name = False

		while not is_potential_valid_sticker_name:

			try:
				bot.create_new_sticker_set(	user_id = user_id,
											name = new_sticker_name,
											title = f"{title} @RekcitsEnilbot",
											png_sticker = sticker0,
											emojis = get_random_emoji())
				is_potential_valid_sticker_name = True
				is_valid_sticker_number = True

			except BadRequest as e:

				if str(e) == "Shortname_occupy_failed" or str(e) == "Sticker set name is already occupied":
					# A special error that I don't know what cause it.
					# Telegram say that this is an internal error.....
					new_sticker_name = f"backup_{backup_count}_{sticker_name}"
					backup_count = backup_count + 1
					is_potential_valid_sticker_name = True
				else:
					print("??????")
					print(e)
					return

	sticker_name = new_sticker_name[:]


	# the left images to be uploaded
	for idx, url in enumerate(urls[1:]):
		sticker_image = get_sticker_image_from_url(is_message_sticker, url)

		sticker_image.save(f"{sticker_number}.png")

		try:
			sticker = bot.upload_sticker_file(	user_id = user_id,
												png_sticker=open(f"{sticker_number}.png", 'rb')).file_id
		except Exception as e:
			w, h = sticker_image.size
			print(w, h)
			print(url)
			print(e)
			return

		bot.add_sticker_to_set(	user_id=user_id,
								name = sticker_name,
								png_sticker = sticker,
								emojis = get_random_emoji())

		upload_text = f"{upload_static_text}{'*' * (idx + 2)}{'_' * (len(urls) - (idx + 2))}{idx + 2}/{len(urls)}"
		bot.edit_message_text(	chat_id = user_id,
								message_id = output_message_id,
								text = upload_text)

	# delete temporary file
	os.remove(f"{sticker_number}.png")

	# finish uploading
	bot.send_message(	chat_id = user_id,
						text = (f"噠啦～☆\n\n"
								f"Finished!\n\n"
								f"Line sticker number:{sticker_number}\n"
								f"https://t.me/addstickers/{sticker_name}"))
	# send the first sticker of sticker set
	bot.send_sticker(	chat_id = user_id,
						sticker = sticker0,
						reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(	text = title,
																					url=f"https://t.me/addstickers/{sticker_name}")]]))

	return

# when user type "/start"
def start(update: Update, context: CallbackContext):
	update.message.reply_text(text = (	"這個Bot可以將Line上的貼圖轉換成telegram上的貼圖。\n"
										"This bot can transform Line's stickers to Telegram's sticker.\n\n"
										"只需將貼圖商店的網址貼上來就會自動轉換\n"
										"Send me URL of line sticker to convert.\n\n"+
										"範例example：\n"
										"https://store.line.me/stickershop/product/3962468/ja"))
	return

# when user type "/help"
def help_(update: Update, context: CallbackContext):
	update.message.reply_text(text = (	"直接傳網址給我就可以惹\n"
										"Just send me the URL.\n\n"
										"像這個Like this:\n"
										"https://store.line.me/stickershop/product/3962468/ja"))

	return

# when user type "/about"
def about(update: Update, context: CallbackContext):
	update.message.reply_text(text = (	"Author: @Homura343\n"
										"Channel: https://t.me/ArumohChannel\n"
										"Channel Group: https://t.me/ArumohChannelGroup\n"
										"Github: https://github.com/Mescury/Teleline-sticker-converter"))
	return

# when user send message
# simply send response and enqueue procession
def text(update: Update, context: CallbackContext):
	message = update.message.reply_text(text = (	"正在試試看這東西\n"
													"Testing this message."))

	q.enqueue(process_text, update.message.bot.token, update.effective_message.chat_id, update.message.text, message.message_id)
	return

# TeleLine's Dispatcher
# process update from telegram
class Dispatcher(Dispatcher):
	def __init__(self, access_token):
		# initialize the dispatcher
		self.bot = telegram.Bot(token=access_token)
		super().__init__(self.bot, None)

		# initialize handler
		super().add_handler(CommandHandler('start', start))
		super().add_handler(CommandHandler('help', help_))
		super().add_handler(CommandHandler('about', about))
		super().add_handler(MessageHandler(Filters.text, text))

	def process_update(self, data):
		update = Update.de_json(data, self.bot)
		super().process_update(update)