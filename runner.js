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
	// Redirect to remote control page
	function returnToControlPage(error, stdout, sterr)
	{
	exec("pgrep pycam.py", { timeout : 500 },
		function (error, stdout, sterr) {
			response.writeHead(302, {
				'Location': 'https://www.mekeke.co.uk/picam/index.php'
				// 'Location': 'https://192.168.0.109/pycam_php_control/index.php'
				//add other headers here...
			  });
			  response.end();
		});
	}

	// First, decrypt the encrypted command encoded in the url path
	var encrypted = request.url.substring(1);
	console.log("Request headers:");

	const { headers } = request;

	for (const [key, value] of Object.entries(headers)) {
		console.log(`${key}: ${value}`);
	}

	try 
	{
		var decrypted = key.decrypt(encrypted, 'utf8');
		// Then split into command and number
		var components = decrypted.split('/');
		if (components.length == 2)
		{
			command = components[1];
      console.log("command = " + command);
			if (command == "Start" || command == "Stop")
			{
				var newNumber = parseInt(components[0],10);
				// Check that newNumber > lastNumber : prevent repeat attacks
				if (newNumber > lastNumber)
				{
					exec("pgrep pycam.py", { timeout : 500 }, 
					function (error, stdout, sterr) {
						var running = (stdout != '');
						if ((command == "Start") != running)
						// Start or Stop before displaying the updated state.
						command = "sudo /etc/init.d/pycam " + (command.toLowerCase());
						exec(command, { timeout: 1000 }, returnToControlPage);
					});

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

http.createServer(onRequest).listen(8998);