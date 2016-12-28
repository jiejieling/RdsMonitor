/* Info Widget
* ====================== */

var InfoWidget2 = BaseWidget.extend({

  initialize : function() {  

    this.Name = "Info Widget2"

    this.init()
    this.updateFrequency = 5000 // every 5 seconds
        
    var slaveTemplateSource   = $("#slave-template").html()
    this.slaveTemplate  = Handlebars.compile(slaveTemplateSource)
  }
  
, render: function() {
    var model = this.model.toJSON()
      , slaveMarkup = '';    

    if (model.role == "master")
    {
      // templates
      var templateSource        = $("#info-widget-template2-master").html()

      for(var i = 0, len = model.connected_slaves; i < len; i++) {
        slaveMarkup += this.slaveTemplate(model['slave' + i])
      }

    }else{
      // templates
      var templateSource        = $("#info-widget-template2-slave").html()
    }

    this.template         = Handlebars.compile(templateSource)

    var markUp        = this.template(model)

    $(this.el).html(markUp)
      
    $('#slave-infos').popover({
                               "title" : "slaves"
                             , "content" : slaveMarkup
                             })    
  }

})