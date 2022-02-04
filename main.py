from flask import Flask,request
import logging
import TeleLine
import os

# log setting
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					level=logging.INFO)
logger = logging.getLogger(__name__)

# instance bot
dispatcher = TeleLine.Dispatcher(access_token = os.environ.get('TELEGRAM_BOT_TOKEN'))

# setup flask
app = Flask(__name__)

@app.route('/hook', methods=['POST'])
def webhook_handler():
	if request.method == "POST":
		dispatcher.process_update(request.get_json(force=True))
	return 'ok'

# main
if __name__ == "__main__":
	app.run(debug=True)