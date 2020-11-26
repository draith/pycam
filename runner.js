// Runner: receive requests to run or stop pycam, and show current status.
const WebSocket = require('ws');
const child_process = require('child_process');
const fs = require('fs');
const https = require('https');
const exec = child_process.exec;
var NodeRSA = require('node-rsa');
var key = new NodeRSA(fs.readFileSync('./key.pem','utf8'));

const server = https.createServer({
	cert: fs.readFileSync('./self_cert.pem'),
	key: fs.readFileSync('./self_key.pem')
});

const wss = new WebSocket.Server({ server: server });

wss.on('connection', function connection(ws) {

	function sendStatus() {
		exec("pgrep pycam.py", { timeout : 500 },
		function (error, stdout, sterr) {
			var running = (stdout != '');
			ws.send(
				JSON.stringify(
				{ 'status'  : (running ? 'Running' : 'Stopped')
				})
			);
		});
	}

	console.log('Connection open');
	sendStatus();
	var sessionNumber = null;

	ws.on('message', function incoming(encrypted)
	{
		var msg = key.decrypt(encrypted, 'utf8');
		console.log('received: %s', msg);
		var splitPos = msg.indexOf('/');
		if (splitPos < 1)
		{
			console.log('Bad message - delimiter not found.');
			return;
		}

		var newNumber = parseInt(msg.substring(0, splitPos));

		if (isNaN(newNumber))
		{
			console.log('Bad message - no valid number.');
			return;
		}

		var command = msg.substring(splitPos + 1);

		if (!sessionNumber)
		{
			var lastNumber = parseInt(fs.readFileSync('./lastNum.txt','utf8'));
			if (newNumber <= lastNumber)
			{
				console.log('BAD NUMBER! ' + newNumber + ": should be > " + lastNumber);
				return;
			}
			// Valid session number: save it.
			sessionNumber = newNumber;
			fs.writeFileSync("./lastNum.txt", newNumber.toString());
		}
		else if (newNumber != sessionNumber)
		{
			console.log('BAD NUMBER! ' + newNumber + ': should match session number ' + sessionNumber);
			return;
		}

		switch (command)
		{
		case 'Start': 
		case 'Stop':
			console.log("Command = " + command);
			exec("pgrep pycam.py", { timeout : 500 }, 
				function (error, stdout, sterr) {
				var running = (stdout != '');
				// Start or Stop before displaying the updated state.
				command = "sudo /etc/init.d/pycam " + command.toLowerCase();
				exec(command, { timeout: 1000 }, 
					function (error, stdout, sterr) {
						sendStatus();
					});
			});
			break;

		case 'Status':
			sendStatus();
			break;

		default:
			console.log('Unknown command %', msg);
		};
	}); // on 'message'
}); // on 'connection'

server.listen(8998);
