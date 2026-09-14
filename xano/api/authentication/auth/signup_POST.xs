// Signup and retrieve an authentication token
query "auth/signup" verb=POST {
  api_group = "Authentication"

  input {
    text name?
    email email? filters=trim|lower
    text password?
  }

  stack {
    // Check if a user record with that email exists
    db.get user {
      field_name = "email"
      field_value = $input.email
    } as $user
  
    // Verify that the email being used to sign up is unique
    precondition ($user == null) {
      error_type = "accessdenied"
      error = "An account with this email already exists."
    }
  
    // Create a new user record
    db.add user {
      data = {
        created_at: "now"
        name      : $input.name
        email     : $input.email
        password  : $input.password
        role      : "member"
      }
    } as $user
  
    // Create an authentiction token
    security.create_auth_token {
      table = "user"
      extras = {}
      expiration = 86400
      id = $user.id
    } as $authToken
  
    // Create an event log for signup
    function.run "Quick Start/log_event" {
      input = {user_id: $user.id, action: "signup", metadata: $user}
    } as $event_log
  }

  response = {authToken: $authToken, user_id: $user.id}
  tags = ["xano:quick-start"]
  guid = "YY0A9CZxcz-rnp_XKQbX5I7Sm_A"
}