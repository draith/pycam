// Runner: receive requests to run or stop pycam.
var http = require("http");
var fs = require("fs");
var child_process = require('child_process');
var exec = child_process.exec;
var lastNumber = parseInt(fs.readFileSync('lastNum.txt','utf8'),10);

function onRequest(request, response)
{
	// Display current status and link to start or stop.
	function showPage(error, stdout, sterr)
	{
	exec("pgrep pycam.py", { timeout : 500 }, 
		function (error, stdout, sterr) {
			var running = (stdout != '');
			response.writeHead(200, {"Content-Type": "text/html"});
			response.write(fs.readFileSync('runnertop.html'));
			response.write(running ? "<h2 style='color:green;'> Running " :
			                         "<h2 style='color:red;'> Stopped ");
			response.end();
		});
	}

	// First, decrypt the encrypted command encoded in the url path
	exec("./decrypt.sh " + request.url.substring(1), { timeout : 200 },
	function (error, stdout, stderr) {
		// Decrypted command should consist of <command>/<number>
		var components = stdout.split('/');
		if (components.length == 2)
		{
			// Check that number > last number : prevent repeat attacks
			console.log('command = ' + components[0]);
			var newNumber = parseInt(components[1],10);
			console.log('newNumber = ' + newNumber);
			if (newNumber <= lastNumber)
			{
				console.log('newNumber is not greater than lastNumber ' + lastNumber);
			}
			else
			{
				lastNumber = newNumber;
				command = components[0];
				if (command == "Switch")
				{
					// Save new number
					fs.writeFileSync("lastNum.txt", newNumber.toString());
					exec("pgrep pycam.py", { timeout : 500 }, 
					function (error, stdout, sterr) {
						var running = (stdout != '');
						// Start or Stop before displaying the updated state.
						command = "sudo /etc/init.d/pycam " + (running ? 'stop' : 'start');
						exec(command, { timeout: 500 },
							showPage
							);
					});
				}
				else if (command == "Status")
				{
					// Save new number
					fs.writeFileSync("lastNum.txt", newNumber.toString());
					// Just display the current state.
					showPage();
				}
			}
		}
	});
} // onRequest

http.createServer(onRequest).listen(8998);
