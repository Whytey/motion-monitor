function IO(widget, refreshRate) {
//	this.url = "wsgi";
	this.url = "http://benchmill2.thewhytehouse.org/motion-monitor/wsgi";
	this.widget = widget;
	this.refreshRate = refreshRate;
	
	this.getData = function() {
        console.log(this);
		var widget = this.widget;
		var that = this; //What a hack!!!
		$.ajax({
	        type: "POST",
	        url: this.url,
	        data: JSON.stringify(widget.postData),
	        dataType: 'json',
	
	        async: true, /* If set to non-async, browser shows page as "Loading.."*/
	        cache: false,
	        timeout:5000, /* Timeout in ms */
	        
	        success: $.proxy(function(data){ /* called when request completes */
	            widget.handleData(data);
	            if (that.refreshRate != null) {
		            setTimeout(
		            	function() { that.getData(); }, /* Request next poll */
		            	that.refreshRate
		            );
	            }
	        }, this),
	        error: $.proxy(function(XMLHttpRequest, textStatus, errorThrown){
	        	widget.handleError(textStatus);
	        	setTimeout(
	                this.getData, /* Try again after.. */
	                15000); /* milliseconds (15seconds) */
	        }, this)
	    });
	}
}