var express     = require('express');
var app         = express();
var bodyParser  = require('body-parser');
var morgan      = require('morgan');
var os          = require("os");

var config = require('./config');
    
// =======================
// configuration =========
// =======================
var port = process.env.PORT || 8080;
var hostname = os.hostname();

app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());

// use morgan to log requests to the console
app.use(morgan('dev'));


// API ROUTES -------------------
var apiRoutes = express.Router(); 

//Cart
apiRoutes.get('/catalog', function(req, res) {
    res.json({message: "This is the CATALOG microservice served from " + hostname});
});   


// apply the routes  with the prefix /api
app.use('/api', apiRoutes);

// start the server 
app.listen(port);
console.log('Serving CATALOG microservice on http://localhost:' + port);
