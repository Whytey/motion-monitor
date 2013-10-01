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
	
	    $(json.camera).each(function(index, camera) {
	        var tr = tbl.insertRow(-1);
	        
	        var idCell = tr.insertCell(-1);
	        idCell.appendChild(document.createTextNode(camera.id));
	        
	        var stateCell = tr.insertCell(-1);
	        stateCell.appendChild(document.createTextNode(camera.state));

	        var imageCell = tr.insertCell(-1);
	    	var imageElementId = "camera" + camera.id + "Image";

	    	var imageElement = document.createElement("image");
	        imageElement.setAttribute("id", imageElementId);
	    	imageCell.appendChild(imageElement);

	    	var image = new JPEGImage(imageElementId, "1", camera.id, camera.last_snapshot_timestamp, "true");
	    	var io = new IO(image, null);
	    	io.getData();

	        var lastMotionCell = tr.insertCell(-1);
	    });
	    
	    var div = document.getElementById(this.tagId);
	    div.innerHTML = tbl.outerHTML;
	}
}