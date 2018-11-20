// Runner: receive requests to run or stop pycam, and show current status.
var http = require("http");
var fs = require("fs");
var child_process = require('child_process');
var exec = child_process.exec;
var path = "/home/pi/pycam/";
var lastNumber = parseInt(fs.readFileSync(path + 'lastNum.txt','utf8'),10);
var NodeRSA = require('node-rsa');
var key = new NodeRSA(fs.readFileSync(path + 'key.pem','utf8'));
function onRequest(request, response)
{
  console.log("Got request: " + request.url);
	// Display current status - running if pgrep returns non-empty string
	function showStatus(error, stdout, sterr)
	{
	exec("pgrep pycam.py", { timeout : 500 },
		function (error, stdout, sterr) {
			var running = (stdout != '');
			response.writeHead(200, {"Content-Type": "text/plain"});
			response.end(running ? "Running" : "Stopped");
		});
	}
	// First, decrypt the encrypted command encoded in the url path
	var encrypted = request.url.substring(1);
	try 
	{
		var decrypted = key.decrypt(encrypted, 'utf8');
		// Then split into command and number
		var components = decrypted.split('/');
		if (components.length == 2)
		{
			command = components[0];
      console.log("command = " + command);
			if (command == "Status" || command == "Switch")
			{
				var newNumber = parseInt(components[1],10);
				// Check that newNumber > lastNumber : prevent repeat attacks
				if (command != "Status" && newNumber > lastNumber)
				{
					exec("pgrep pycam.py", { timeout : 500 }, 
					function (error, stdout, sterr) {
					var running = (stdout != '');
					// Start or Stop before displaying the updated state.
					command = "sudo /etc/init.d/pycam " + (running ? 'stop' : 'start');
					exec(command, { timeout: 1000 }, showStatus);
					});
				}
				else
				{
					// Just display the current state.
					showStatus();
				}
				if (newNumber > lastNumber)
				{
					// Save new number
					fs.writeFileSync(path + "lastNum.txt", newNumber.toString());
					lastNumber = newNumber;
				}
			}
		}
	}
	catch (err)
	{
		// key.decrypt will throw an error if an invalid command string is received.
		// Catch this to protect us from DoS attacks.
		console.log("Caught error: " + err.message);
	}
} // onRequest

//http.createServer(onRequest).listen(8998);
http.createServer(onRequest).listen(80);
