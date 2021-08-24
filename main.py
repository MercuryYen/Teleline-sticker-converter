from flask import Flask,request
import configparser
import logging
import TeleLine

# log setting
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					level=logging.INFO)
logger = logging.getLogger(__name__)

# read config file
config = configparser.ConfigParser()
config.read('config.ini')

# instance bot
dispatcher = TeleLine.Dispatcher(access_token = config['TELEGRAM']['ACCESS_TOKEN'])

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