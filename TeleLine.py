#coding=utf8
from telegram import InlineKeyboardButton,InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, Dispatcher, CommandHandler, MessageHandler, Filters
from telegram.error import BadRequest
import telegram

import requests

from bs4 import BeautifulSoup

from io import BytesIO
from PIL import Image

import moviepy.editor as mp
from apnggif import apnggif

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
like sticker_type, title, image urls

when sticker_type is {normal, animated}
	urls is a list of sting
when sticker_type is message, 
	urls is a list of list of string standing for pairs of images (background image and text image)
'''
def get_sticker_info(text):
	# convert to soup
	soup = BeautifulSoup(text, "html.parser")
	
	# output
	# "normal", "message", "animated"
	sticker_type = "normal"
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
			sticker_type = "message"

		# custom stickers
		elif text.find("mdCMN09Image FnCustomBase") != -1:
			classes = soup.find_all("span", "mdCMN09Image FnCustomBase")
			text = [t["style"] for t in classes]
			urls = [t[t.find("(")+1:t.find(";")] for t in text]
			urls = list(dict.fromkeys(urls))
			sticker_type = "normal"

		# animated stickers
		elif text.find('animationUrl&quot; : &quot;http') != -1:
			classes = soup.find_all("li", "mdCMN09Li FnStickerPreviewItem")
			texts = [c["data-preview"] for c in classes]
			urls = [t[t.find("animationUrl")+17:] for t in texts]
			urls = [t[:t.find(".png")+4] for t in urls] 
			sticker_type = "animated"

		# other normal stickers
		else:
			classes = soup.find_all("span", "mdCMN09Image")
			text = [t["style"] for t in classes]
			urls = [t[t.find("(")+1:t.find(";")] for t in text]
			urls = list(dict.fromkeys(urls))
			sticker_type = "normal"
		
		c = soup.find("p", "mdCMN38Item01Ttl")
		title = c.text
	except Exception as e:
		print(e)
		sticker_type = "None"
		title = ""
		urls = []

	if sticker_type == "normal" and len(urls) > 0:
		for idx in range(len(urls)):
			urls[idx] = urls[idx].replace(")", "")

	return sticker_type, title, urls

# get sticker name from sticker number
def get_sticker_name_from_sticker_number(bot, sticker_type, sticker_number):
	if sticker_type != "animated":
		return f"line{sticker_number}_by_{bot.username}"
	else:
		return f"line{sticker_number}_animated_by_{bot.username}"

# get telegram sticker set based on name of sticker
def get_sticker_set(bot, sticker_name):
	
	result = None
	try:
		result = bot.get_sticker_set(name=sticker_name)
	except Exception as e:
		print(e)
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
	proportion = maximum / max(w,h)

	new_w = round(w * proportion)
	new_h = round(h * proportion)
	if new_w >= new_h: new_w = maximum
	if new_h >= new_w: new_h = maximum

	return image.resize((new_w, new_h), Image.BICUBIC)

# resize clip to have the max dimension be a specific number
# 5x10, 20 -> 10x20
# 10x20, 5 -> 3x5 where 3 standing for round(2.5)
def resize_clip_with_maximum(clip, maximum):
	w, h = clip.size
	proportion = maximum / max(w,h)

	new_w = round(w * proportion)
	new_h = round(h * proportion)
	if new_w >= new_h: new_w = maximum
	if new_h >= new_w: new_h = maximum

	return clip.resize((new_w, new_h))

# convert an apng file to clip
def apng_to_clip(image_file_name):
	apnggif(image_file_name)
	return mp.VideoFileClip(f"{image_file_name.split('.')[0]}.gif")


# a function to save the file using url
def save_file_from_url(url, name):
	with open(name, "wb") as f:
		f.write(requests.get(url).content)

# get image with telegram sticker format from image url 
# when sticker_type is normal, url should be a image url
# when sticker_type is message, url should be a list of image urls
# when sticker_type is animated, url should be a apng url

# step:
# 1. download image
# (1.5. if sticker_type is message, merge images)
# 2. resize to ??? x 512 or 512 x ??? (where ??? <= 512)
def get_sticker_from_url(sticker_type, url):
	# get image from url
	if sticker_type == "normal":
		image = get_image_from_url(url)
		image = resize_image_with_maximum(image, 512)
		return image

	elif sticker_type == "message":
		background_image = get_image_from_url(url[0])
		text_image = get_image_from_url(url[1])
		image = merge_image(background_image, text_image)
		image = resize_image_with_maximum(image, 512)
		return image

	elif sticker_type == "animated":
		save_file_from_url(url, "temp.png")
		clip = apng_to_clip("temp.png").set_duration(3)
		clip = resize_clip_with_maximum(clip, 512)
		return clip

	else:
		raise Exception("Not a normal sticker type: %s" % sticker_type)

	


# main procession of stickers
# download stickers, resize stickers, upload stickers
def process_text(access_token, user_id, sticker_number, sticker_type, title, urls, output_message_id):

	bot = telegram.Bot(token=access_token)

	sticker_name = get_sticker_name_from_sticker_number(bot, sticker_type, sticker_number)

	has_uploaded_first_sticker = False
	
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
								f"發現{len(urls)}張貼圖，轉換需要一段時間，完成時會再通知\n\n"
								f"Found {len(urls)} stickers. You will be notified when finishing converting\n")

		# first image for creating a sticker set
		if not has_uploaded_first_sticker:
			sticker_file = get_sticker_from_url(sticker_type, urls[0])

			if sticker_type != "animated":
				sticker_file.save(f"{sticker_number}.png")
				sticker0 = bot.upload_sticker_file(	user_id = user_id,
													png_sticker=open(f"{sticker_number}.png", 'rb')).file_id
			else:
				sticker_file.write_videofile(f"{sticker_number}.webm", codec = "libvpx-vp9", audio = False, fps=30, ffmpeg_params = ["-pix_fmt", "yuva420p", "-t", "3"])
				sticker0 = f"{sticker_number}.webm"

			has_uploaded_first_sticker = True

		# create a sticker set
		is_potential_valid_sticker_name = False

		while not is_potential_valid_sticker_name:

			try:
				if sticker_type != "animated":
					bot.create_new_sticker_set(	user_id = user_id,
												name = new_sticker_name,
												title = f"{title} @RekcitsEnilbot",
												png_sticker = sticker0,
												emojis = get_random_emoji())
				else:
					bot.create_new_sticker_set(	user_id = user_id,
												name = new_sticker_name,
												title = f"{title} @RekcitsEnilbot",
												webm_sticker = open(sticker0, 'rb'),
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
					print(sticker0)
					print("??????")
					print(e)
					return

	sticker_name = new_sticker_name[:]


	# the left images to be uploaded
	for idx, url in enumerate(urls[1:]):
		sticker_file = get_sticker_from_url(sticker_type, url)

		if sticker_type != "animated":
			sticker_file.save(f"{sticker_number}.png")
		else :
			sticker_file.write_videofile(f"{sticker_number}.webm", codec = "libvpx-vp9", audio = False, fps=30, ffmpeg_params = ["-pix_fmt", "yuva420p", "-t", "3"])

		if sticker_type != "animated":
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
		else:
			bot.add_sticker_to_set(	user_id=user_id,
									name = sticker_name,
									webm_sticker = open(f"{sticker_number}.webm", 'rb'),
									emojis = get_random_emoji())

		upload_text = f"{upload_static_text}{'*' * (idx + 2)}{'_' * (len(urls) - (idx + 2))}{idx + 2}/{len(urls)}"
		bot.edit_message_text(	chat_id = user_id,
								message_id = output_message_id,
								text = upload_text)

	# delete temporary file
	if sticker_type != "animated":
		os.remove(f"{sticker_number}.png")
	else:
		os.remove(f"{sticker_number}.gif")
		os.remove(f"{sticker_number}.webm")
		os.remove(f"temp.png")
		os.remove(f"temp.gif")

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
def text_(update: Update, context: CallbackContext):
	message = update.message.reply_text(text = (	"正在試試看這東西\n"
													"Testing this message."))

	bot = telegram.Bot(token=update.message.bot.token)

	# check if text is valid
	try:
		# check if there is a sticker number in text 
		sticker_number = get_sticker_number_from_url(update.message.text)
		if sticker_number == "":
			raise Exception("Can't find any sticker number in text")
		
		# check if text is an url
		n = requests.get(update.message.text)

	except Exception as e:
		print(e)
		bot.edit_message_text(	chat_id = update.effective_message.chat_id,
								message_id = message.message_id,
								text = ("無效網址\n\n"
										"Invalid URL"))
		return

	sticker_type, title, urls = get_sticker_info(n.text)

	# can't find any sticker
	if len(urls) == 0:
		bot.edit_message_text(chat_id = update.effective_message.chat_id,
							message_id = message.message_id,
							text = 	("沒有找到任何Line貼圖？！\n\n"
									"Can't find any line sticker?!"))
		return

	# check if there is an existing sticker set
	sticker_name = get_sticker_name_from_sticker_number(bot, sticker_type, sticker_number)
	sticker_set = get_sticker_set(bot, sticker_name)
	if sticker_set != None:
		# exist sticker set, check if there are true number of stickers
		if len(sticker_set.stickers) == len(urls):
			bot.edit_message_text(	chat_id = update.effective_message.chat_id,
									message_id = message.message_id,
									text = (	f"總算找到了\n"
												f"This one?!\n\n"
												f"Line sticker number:{sticker_number}"))

			bot.send_sticker(	chat_id = update.effective_message.chat_id,
								sticker = sticker_set.stickers[0].file_id,
								reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(	text = title, 
																							url = f"https://t.me/addstickers/{sticker_name}")]]))
			return

	# need to create stickerset
	q.enqueue(process_text, update.message.bot.token, update.effective_message.chat_id, sticker_number, sticker_type, title, urls, message.message_id)
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
		super().add_handler(MessageHandler(Filters.text, text_))

	def process_update(self, data):
		update = Update.de_json(data, self.bot)
		super().process_update(update)