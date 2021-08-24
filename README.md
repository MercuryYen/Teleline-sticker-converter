# Teleline-sticker-converter
這個Bot可以將Line上的貼圖轉換成telegram上的貼圖<p>
This bot can transform Line's stickers to Telegram's sticker.<p>
# 食用方法
把 config.ini 裡面的 ACCESS_TOKEN 替換成自己的 Telegram bot token<p>
把他丟到Heroku<p>
然後連接到telegram bot就可以了<p>

Throw all files to Heroku. Link to telegram bot and expect it would work.

# 檔案
main.py 處理網路的地方<p>
TeleLine.py 處理所有資料並和user講話<p>
worker.py 是個Heroku限定的東東，可以做出Background Task之類的神奇效果，不用限制於Webhook的30秒<p>