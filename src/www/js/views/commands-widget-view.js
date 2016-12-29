var CommandsWidget = BaseWidget.extend({

    initialize : function() {

      this.Name = "Commands Widget"

      this.init()      
      
      // templates
      var templateSelector = "#commands-widget-template"
        , templateSource = $(templateSelector).html()
        
      this.template = Handlebars.compile(templateSource)
      this.$el.empty().html(this.template())

      // chart
      this.chart = new google.visualization.LineChart($("#commands-widget-chart").empty().get(0))
      this.dataTable = new google.visualization.DataTable()
      this.dataTable.addColumn('datetime', 'datetime')
      this.dataTable.addColumn('number', 'Commands Processed')      
    }

  , render : function() {

      var model = this.model.toJSON()
        , markUp = this.template(model)
        , self = this

      self.dataTable.removeRows(0,self.dataTable.getNumberOfRows())
            
      $.each(model.data, function(index, obj){          
          // obj[0] = timestamp
    	  // obj[1] = commands, it's a increasing number
    	  if(index == 0)
    		  return true
    		  
          var recordDate = new Date(obj[0] * 1000)
          
          if(self.dataTable)
            self.dataTable.addRow( [recordDate, obj[1] - model.data[index - 1][1]] )
      })
     
      var pointSize = model.data.length > 120 ? 1 : 5
        , options = {
                      title : ''
                    , colors: [ '#17BECF', '#9EDAE5' ]
                    , areaOpacity : .9                    
                    , pointSize: pointSize                      
                    , chartArea: { 'top' : 10, 'width' : '85%' }
                    , width : "100%"
                    , height : 200
                    , animation : { duration : 500, easing: 'out' } 
                    , vAxis: { minValue : 0 }
                    }

      this.chart.draw(this.dataTable, options)
    }
})