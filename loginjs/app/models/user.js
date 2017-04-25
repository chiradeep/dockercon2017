var Users = {
              'test': {name: 'Test User', password: 'password', admin: true},
              'foo':  {name: 'Foo User', password: 'password', admin: false}
};

module.exports = {
    findOne: function(username, callback) {
        console.log("going to find user " + username['name'])
        callback(null, Users[username['name']]);
    },
    find: function(ignore, callback) {
        callback(null, Users)
    }
}
