var BaseWidget = Backbone.View.extend({

  enableLogging : false

, updateFrequency : 30 * 1000 //30s

, Name : "BaseWidget"

, server : ""

, events : {
             "click .time-period" : "ChangeTimeFrame"
           , "click .go" : "Go"          
           }

, init : function () {

      var self = this

      $(document).on("ServerChange", function(e, server){      
        self.server = server
        self.UpdateModel(true)
      })    

      this.timer = setInterval( function () { self.UpdateModel(true) }, this.updateFrequency )      

      // set event listners
      this.model
        .on("error", this.error, this)
        .on("change", this.ModelChanged, this)       
      
  }

, UpdateModel : function ( enableTimer ) {    

    clearInterval(this.timer)    

    this.startTime = new Date()

    this.model.fetch({
        data : {
          // if no from/to are found, provide reasonable defaults of one day ago and now, respectively
          from : this.$el.find('[name=from]').val() || parseInt(new Date(new Date() - 1 * 24 * 60 * 60 * 1000).getTime() / 1000)
        , to : this.$el.find('[name=to]').val() || parseInt(new Date().getTime() / 1000)
        , server : this.server
      }
    })

    this.enableTimer = enableTimer
   
  }

, ModelChanged : function(){

    this.endTime = new Date()
    var timeElapsed = (this.endTime - this.startTime);
    
    if (this.enableLogging)
      console.log(this.Name + ": Time Elapsed = " + timeElapsed + " ms")

    this.render()

    if(this.enableTimer)     
    {
      var self = this
      this.timer = setInterval( function () { self.UpdateModel(true) }, this.updateFrequency )              
    }
} 

, Go : function( el ) {
    this.UpdateModel(false)
  }

, ChangeTimeFrame : function ( el ) {

    var selectionType = $(el.target).data("type")
      , timeFrame = parseInt( $(el.target).data("time") )

    // update the dropdown's label
    $(el.target)
      .closest(".btn-group")
      .children()
      .first()
      .text($(el.target).text())

    // Custom time frame selected
    if ( selectionType == "custom" ) {
      $(el.target)
        .closest(".btn-group")
        .siblings(".date-control")
        .css("display","inline")      
    }
    // real time    
    else if ( selectionType == "realtime" ) {
      $(el.target)
        .closest(".btn-group")
        .siblings(".date-control")
        .css("display","none")
      
      var self = this
      this.$el.find('[name=from]').val("")
      this.$el.find('[name=to]').val("")
      this.timer = setInterval( function () { self.UpdateModel(true) }, this.updateFrequency )      
    }
    // one of the template time frame selected
    // example: last 15mins, last 1 day etc    
    else {

      $(el.target)
        .closest(".btn-group")
        .siblings(".date-control")
        .css("display","none")      

      var endDate = parseInt(new Date().getTime() / 1000)
        , startDate = endDate          

      switch(selectionType) {

        case 'minute' : 
          startDate = parseInt(new Date(endDate - timeFrame * 60 * 1000).getTime() / 1000)
          break
                       
        case 'hour' :  
          startDate = parseInt(new Date(endDate - timeFrame * 60 * 60 * 100).getTime() / 1000)
          break

        case 'day' :  
          startDate = parseInt(new Date(endDate - timeFrame * 24 * 60 * 60 * 1000).getTime() / 1000)
          break

        case 'week' :  
          startDate = parseInt(new Date(endDate - timeFrame * 7 * 24 * 60 * 60 * 1000).getTime() / 1000)
          break

        case 'month' :  
          startDate = parseInt(new Date(endDate - timeFrame * 30 * 24 * 60 * 60 * 1000).getTime() / 1000)
          break
      }

      this.$el.find('[name=from]').val(startDate)
      this.$el.find('[name=to]').val(endDate)              
      this.UpdateModel(false)

    }
  }


, error: function ( model, error ) {
   if (this.enableLogging)
      console.log(this.Name + ": Error Occured \n" + error + "\n" + model )

  }
        
})
