function CameraSummary(tagId) {
	this.tagId = tagId;
	
	this.refreshRate = 5000;
	
	this.postData = {
            method:"camera.get",
            params:{}
         };	
	
	this.handleData = function(json) {
	    console.log("Handling camera_summary data");

	    var tbl  = document.createElement("table");
	    tbl.style.width="100%";
	    tbl.style.border = "1px; solid; black;";

	    var header = tbl.createTHead();
	    var headerRow = header.insertRow(0);
	    var cell = headerRow.insertCell(-1);
	    cell.innerHTML = "<b>Camera</b>";
	    cell = headerRow.insertCell(-1);
	    cell.innerHTML = "<b>State</b>";
	    cell = headerRow.insertCell(-1);
	    cell.innerHTML = "<b>Snapshot</b>";
	    cell = headerRow.insertCell(-1);
	    cell.innerHTML = "<b>Last Motion</b>";
	
	    $(json.result).each(function(index, camera) {
	        var tr = tbl.insertRow(-1);
	        
	        var idCell = tr.insertCell(-1);
	        idCell.appendChild(document.createTextNode(camera.cameraId));
	        
	        var stateCell = tr.insertCell(-1);
	        stateCell.appendChild(document.createTextNode(camera.state));

	        var snapshotCell = tr.insertCell(-1);
	    	var snapshotElementId = "camera" + camera.cameraId + "Snapshot";

	    	var snapshotElement = document.createElement("image");
	    	snapshotElement.setAttribute("id", snapshotElementId);
	    	snapshotCell.appendChild(snapshotElement);

	    	var snapshot = new JPEGImage(snapshotElementId, "2", camera.cameraId, camera.lastSnapshot.timestamp, null, "true");
	    	var io = new IO(snapshot, null);
	    	io.getData();

	        var motionCell = tr.insertCell(-1);
	    	var motionElementId = "camera" + camera.cameraId + "Motion";

	    	var motionElement = document.createElement("image");
	    	motionElement.setAttribute("id", motionElementId);
	    	motionCell.appendChild(motionElement);
	    	
	    	if (camera.recentMotion[0] != null) {
		    	var motion = new JPEGImage(motionElementId, "1", camera.cameraId, camera.recentMotion[0].startTime, camera.recentMotion[0].eventId, "true");
		    	var io = new IO(motion, null);
		    	io.getData();
	    	}

	    });
	    
	    var div = document.getElementById(this.tagId);
	    div.innerHTML = tbl.outerHTML;
	}
	
	this.handleError = function(json) {
	    console.log("Handling CameraSummary error: " + json);
	}
}