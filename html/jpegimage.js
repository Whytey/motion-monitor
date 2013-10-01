function JPEGImage(tagId, type, cameraId, timestamp, thumbnail) {
	this.tagId = tagId;
	this.type = type;
	this.cameraId = cameraId;
	this.timestamp = timestamp;
	this.thumbnail = thumbnail;
	
	this.postData = {
            method:"image.get",
            params: {
    			type: this.type,
    			cameraid: this.cameraId,
    			timestamp: this.timestamp,
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
}