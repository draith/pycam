// Runner: receive requests to run or stop pycam.
var http = require("http");
var fs = require("fs");
var base64 = require('base-64');
var child_process = require('child_process');
var exec = child_process.exec;
var key = fs.readFileSync('key.pub','utf8');
var lastNumber = parseInt(fs.readFileSync('lastNum.txt','utf8'),10);

// Returns encoded/decoded text using key
function arc4(text,thekey)
{
  var temp, i, j, n;
  var array = [];
  var result = "";
  
  // First, set up array from key
  for (i = 0; i < 256; i++)
  {
    array[i] = i;
  }
  j = 0;
  for (i = 0; i < 256; i++)
  {
    j = (j + array[i] + thekey.charCodeAt(i % thekey.length)) & 255;
    temp = array[i];
    array[i] = array[j];
    array[j] = temp;
  }
  // Then xor array values with input to get result
  i = 0;
  j = 0;
  for (n = 0; n < text.length; n++)
  {
     i = (i + 1) & 255;
     j = (j + array[i]) & 255;
     temp = array[i];
     array[i] = array[j];
     array[j] = temp;
     result = result + String.fromCharCode(array[(array[i] + array[j]) & 255] ^ text.charCodeAt(n));
  }
  return result;
  
} // arc4

// Function to decode printable base64 encoding.
function arc64_decode(string,key)
{
  return arc4(base64.decode(string),key);
}

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
	try 
	{
	var command = arc64_decode(request.url.substring(1),key);
	// Split tempkey . <command/timestamp>
	var components = command.split('.');
	if (components.length == 2)
	{
		var tempkey = components[0];
		command = components[1];
		command = arc64_decode(command,tempkey);
		components = command.split('/');
	
		if (components.length == 2)
		{
			// Check that number > last number
			console.log('command = ' + components[0]);
			var newNumber = parseInt(components[1],10);
			console.log('newNumber = ' + newNumber);
			if (newNumber <= lastNumber)
			{
				console.log('newNumber is not greater than lastNumber ' + lastNumber);
			}
			else
			{
				fs.writeFileSync("lastNum.txt", newNumber.toString());
				lastNumber = newNumber;
				command = components[0];
				if (command == "Switch")
				{
				exec("pgrep pycam.py", { timeout : 500 }, 
					function (error, stdout, sterr) {
						var running = (stdout != '');
						// Start or Stop before displaying the updated state.
						command = "sudo /etc/init.d/pycam " + (running ? 'stop' : 'start');
						exec(command, { timeout: 500 },
							showPage
							);
						// Save new number
					});
				}
				else if (command == "Status")
				{
					// Just display the current state.
					showPage();
					// Save new number
				}
			}
		}
	}
	} catch(err) { console.log(err.message); }
}

http.createServer(onRequest).listen(8998);
