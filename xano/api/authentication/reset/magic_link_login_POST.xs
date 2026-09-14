// Exchanges magic token for auth token. Logs in user with the one-time link.
query "reset/magic-link-login" verb=POST {
  api_group = "Authentication"

  input {
    text magic_token? filters=trim
    text email? filters=trim
  }

  stack {
    // Check to make sure the magic token exists
    precondition ($input.magic_token != null) {
      error = "magic_token is required but was not provided."
    }
  
    // Check to make sure the email exists
    precondition ($input.email != null) {
      error = "email is required but not provided"
    }
  
    // Get the user record with the email from the URL
    db.get user {
      field_name = "email"
      field_value = $input.email
      output = [
        "id"
        "created_at"
        "name"
        "email"
        "role"
        "password_reset.token"
        "password_reset.expiration"
        "password_reset.used"
      ]
    } as $user
  
    // Validate the UUID matches the hashed value
    security.check_password {
      text_password = $input.magic_token
      hash_password = $user.password_reset.token
    } as $verify_token
  
    // Verify the UUID validation is true
    precondition ($verify_token) {
      error_type = "unauthorized"
      error = "The token did not match"
    }
  
    // Check that the password reset token has not expired
    precondition ($user.password_reset.expiration > now) {
      error = "Magic token has expired. Please request another one."
    }
  
    // Check to make sure the password reset has not been used
    precondition ($user.password_reset.used == false) {
      error = "This magic link has already been used. Please request another one."
    }
  
    // Create an authentication token
    security.create_auth_token {
      table = "user"
      extras = ""
      expiration = 86400
      id = $user.id
    } as $auth_token
  
    // Update the user record that the password reset token has been used
    db.edit user {
      field_name = "id"
      field_value = $user.id
      data = {
        password_reset: {
        token     : $user.password_reset.token
        expiration: $user.password_reset.expiration
        used      : true
      }
      }
    } as $user1
  
    // Create an event log for password reset login
    function.run "Quick Start/log_event" {
      input = {
        user_id : $user.id
        action  : "login_for_password_reset"
        metadata: $user1
      }
    } as $event_log
  }

  response = {authToken: $auth_token, user_id: $user1.id}
  tags = ["xano:quick-start"]
  guid = "ASVQiC1wt5qJN9_U_V7zKbPwn4U"
}