// =======================
// get the packages we need ============
// =======================
var express     = require('express');
var app         = express();
var bodyParser  = require('body-parser');
var morgan      = require('morgan');
var os          = require("os");

var config = require('./config'); // get our config file
    
// =======================
// configuration =========
// =======================
var port = process.env.PORT || 8080; // used to create, sign, and verify tokens
var hostname = os.hostname();

// use body parser so we can get info from POST and/or URL parameters
app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());

// use morgan to log requests to the console
app.use(morgan('dev'));

// =======================
// routes ================
// =======================

// API ROUTES -------------------
var apiRoutes = express.Router(); 

//Cart
apiRoutes.get('/cart', function(req, res) {
    res.json({message: "This is the cart microservice served from " + hostname});
});   



// apply the routes to our application with the prefix /api
app.use('/api', apiRoutes);

// =======================
// start the server ======
// =======================
app.listen(port);
console.log('Serving cart microservice on http://localhost:' + port);
