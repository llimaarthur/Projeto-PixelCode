// Login and retrieve an authentication token
query "auth/login" verb=POST {
  api_group = "Authentication"

  input {
    email email filters=trim|lower
    text password
  }

  stack {
    // Get the user record via email
    db.get user {
      field_name = "email"
      field_value = $input.email
      output = ["id", "name", "email", "password", "role", "status", "must_change_password"]
    } as $user
  
    // Check to make sure a user with that email exists
    precondition ($user != null) {
      error_type = "accessdenied"
      error = "Invalid Credentials."
    }
  
    // Support legacy user records that may still store a plain-text password.
    // In that case, accept the direct match and continue without invoking the hash checker.
    var $legacy_password_match {
      value = (($user.password != null) && ($user.password == $input.password))
    }

    conditional {
      if ($legacy_password_match == true) {
        var $pass_result {
          value = true
        }
      } 
      
      else {
        precondition ($user.password != null && $user.password != "") {
          error_type = "accessdenied"
          error = "Invalid Credentials."
        }

        security.check_password {
          text_password = $input.password
          hash_password = $user.password
        } as $pass_result
      }
    }
  
    // Verify that the password check passed
    precondition ($pass_result == true) {
      error_type = "accessdenied"
      error = "Invalid Credentials."
    }

    precondition ($user.status == "active" || $user.status == "enabled") {
      error_type = "accessdenied"
      error = "Invalid Credentials."
    }
  
    // Create an authentication token
    security.create_auth_token {
      table = "user"
      extras = ""
      expiration = 86400
      id = $user.id
    } as $authToken
  
    // Create an event log for login
    function.run "Quick Start/log_event" {
      input = {
        user_id: $user.id
        action : "login"
        metadata: {role: $user.role}
      }
    } as $event_log
  }

  response = {
    authToken: $authToken
    user_id: $user.id
    user: {
      id: $user.id
      name: $user.name
      email: $user.email
      role: $user.role
      status: $user.status
      must_change_password: $user.must_change_password
    }
    name: $user.name
    email: $user.email
    role: $user.role
    status: $user.status
    must_change_password: $user.must_change_password
  }
  tags = ["xano:quick-start"]
  guid = "1W8ER2WkNZeSjnSxvAYWXWpbVcQ"
}