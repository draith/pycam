// Runner: receive requests to run or stop pycam, and show current status.
var http = require("http");
var child_process = require('child_process');
var exec = child_process.exec;
var url = require("url");


function onRequest(request, response)
{
  function writePage()
  {
    // Display current status - running if pgrep returns non-empty string
    response.writeHead(200, {"Content-Type": "text/html"});
    response.write('<html><head><title>Picam Local Control</title></head><body style="font-size:10vw;"><h1>Picam</h1><h1 style = "color:');
  	exec("pgrep pycam.py", { timeout : 500 },
  		function (error, stdout, sterr) {
  			var running = (stdout != '');
  			response.write(running ? 'green">Running' : 'red">Stopped');
        response.write("</h1>");
        var command = (running ? 'Stop' : 'Start');
        response.write('<h1><a href="/' + command + '">' + command + '</a></h1>');
        response.end('</body></html>');
  		});
  }
  function showStatus(error, stdout, sterr)
  {
    writePage();
  }

  console.log("Got request: " + request.url);
  reqCommand = request.url.substring(1).toLowerCase();
  switch (reqCommand) {
    case 'start':
    case 'stop':
      // Start or Stop before displaying the updated state.
      command = "sudo /etc/init.d/pycam " + reqCommand;
      exec(command, { timeout: 1000 }, showStatus);
      break;
    case '':
      writePage();
      break;
    default:
      response.writeHead(404, {'Content-Type': 'text/plain'});
      response.end('404 Not Found\n');
      response.end();
  }
} // onRequest

http.createServer(onRequest).listen(8765);
