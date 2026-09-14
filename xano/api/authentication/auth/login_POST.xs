// Login and retrieve an authentication token
query "auth/login" verb=POST {
  api_group = "Authentication"

  input {
    email email? filters=trim|lower
    text password?
  }

  stack {
    // Get the user record via email
    db.get user {
      field_name = "email"
      field_value = $input.email
      output = ["id", "created_at", "name", "email", "password", "role"]
    } as $user
  
    // Check to make sure a user with that email exists
    precondition ($user != null) {
      error_type = "accessdenied"
      error = "Invalid Credentials."
    }
  
    // Check that the password matches the hashed password
    security.check_password {
      text_password = $input.password
      hash_password = $user.password
    } as $pass_result
  
    // Verify that the password check passed
    precondition ($pass_result) {
      error_type = "accessdenied"
      error = "Invalid Credentials."
    }
  
    // Create an authentication token
    security.create_auth_token {
      table = "user"
      extras = {}
      expiration = 86400
      id = $user.id
    } as $authToken
  
    // Create an event log for login
    function.run "Quick Start/log_event" {
      input = {user_id: $user.id, action: "login", metadata: $user}
    } as $event_log
  }

  response = {authToken: $authToken, user_id: $user.id}
  tags = ["xano:quick-start"]
  guid = "1W8ER2WkNZeSjnSxvAYWXWpbVcQ"
}