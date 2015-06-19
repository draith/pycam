// Runner: receive requests to run or stop pycam.
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
	// Display current status - running if pgrep returns non-empty string
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
	var encrypted = request.url.substring(1);
	var decrypted = key.decrypt(encrypted, 'utf8');
	// Then split into command and number
	var components = decrypted.split('/');
	if (components.length == 2)
	{
		command = components[0];
		if (command == "Status" || command == "Switch")
		{
			var newNumber = parseInt(components[1],10);
			// Check that newNumber > lastNumber : prevent repeat attacks
			if (command == "Switch" && newNumber > lastNumber)
			{
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
			else
			{
				// Just display the current state.
				showPage();
			}
			if (newNumber > lastNumber)
			{
				// Save new number
				fs.writeFileSync(path + "lastNum.txt", newNumber.toString());
				lastNumber = newNumber;
			}
		}
	}
} // onRequest

http.createServer(onRequest).listen(8998);
