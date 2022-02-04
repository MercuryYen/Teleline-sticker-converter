# Teleline-sticker-converter
這個Bot可以將Line上的貼圖轉換成telegram上的貼圖<p>
This bot can transform Line's stickers to Telegram's sticker.<p>
# 食用方法
1. 在 telegram 的 @BotFather 新增一個 Bot，複製好 access token<p>
2. 在 Heroku 新增一個 app<p>
3. 在該 app 的 Config Vars， 新增 TELEGRAM_BOT_TOKEN 設為剛剛複製好的 token<p>
4. 將該 Bot 的程式丟到 Heroku 上面<p>
5. 在 telegram 把 bot webhook 設為 {app url}/hook 即可

1. Create a new bot using @BotFather in telegram, copy the access token of the bot.<p>
2. Create an app in Heroku.<p>
3. In Config Vars of the app, set TELEGRAM_BOT_TOKEN to the access token.<p>
4. Upload programs of the bot to Heroku.<p>
5. Set heroku worker to >=1
6. In telegram, set the bot's webhook to {app url}/hook.

# 檔案
main.py 處理網路的地方<p>
TeleLine.py 處理所有資料並和user講話<p>
worker.py 是個Heroku限定的東東，可以做出Background Task之類的神奇效果，不用限制於Webhook的30秒<p>