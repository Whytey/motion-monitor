function JPEGImage(tagId, type, cameraId, timestamp, event, thumbnail) {
	this.tagId = tagId;
	this.type = type;
	this.cameraId = cameraId;
	this.timestamp = timestamp;
	this.event = event;
	this.thumbnail = thumbnail;
	
	this.postData = {
            method:"image.get",
            params: {
    			type: this.type,
    			cameraid: this.cameraId,
    			timestamp: this.timestamp,
    			event: this.event,
    			thumbnail: this.thumbnail,
    			include_image: "True"
    		}
         };
	
	this.handleData = function(json) {
		if (json.error) {
			$("#" + tagId).attr("alt", "Error loading image: " + json.error.data);
		}
        $(json.result).each(function(index, image){
        	var image_data = image.image;
    		$("#" + tagId).attr("src", "data:image/jpeg;base64," + image_data);
        });
	}
	
	this.handleError = function(json) {
	    console.log("Handling JPEGImage error");
	}

}