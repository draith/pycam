// Runner: receive requests to run or stop pycam, and show current status.
const WebSocket = require('ws');
const child_process = require('child_process');
const exec = child_process.exec;
const wss = new WebSocket.Server({ port: 8998 });

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
  
	ws.on('message', function incoming(msg) {
		console.log('received: %s', msg);
		commandObj = JSON.parse(msg);
		switch (commandObj.command)
		{
		case 'Start': 
		case 'Stop':
			exec("pgrep pycam.py", { timeout : 500 }, 
				function (error, stdout, sterr) {
				var running = (stdout != '');
				// Start or Stop before displaying the updated state.
				command = "sudo /etc/init.d/pycam " + commandObj.command.toLowerCase();
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
  }); // on 'connect'
