// This function generates a magic token with a 60 minute expiration date.
function "Quick Start/generate_magic_link" {
  input {
    email email?
  }

  stack {
    // Checks that the email input is not empty
    precondition ($input.email != null) {
      error = "email is required but was not suppiled. "
    }
  
    // Gets the user record by email
    db.query user {
      where = $db.user.email == $input.email
      return = {type: "single"}
    } as $user
  
    // Verifies that the user record exists
    precondition ($user != null) {
      error_type = "notfound"
      error = "No user found for that email."
    }
  
    // Creates a unique UUID as token
    security.create_uuid as $token
  
    // Builds the password reset object
    var $password_reset {
      value = {}
        |set:"token":$token
        |set:"expiration":(now
          |add_secs_to_timestamp:(3600|to_int)
        )
        |set:"used":false
    }
  
    // Updates the user record with the password reset object
    db.edit user {
      field_name = "id"
      field_value = $user|get:"id":0
      data = {password_reset: $password_reset}
    } as $updated_password_reset
  }

  response = {token: $token, email: $updated_password_reset.email}
  tags = ["xano:quick-start"]
  guid = "9_XOETQSAzYrpFTeuP9wjNkQy4I"
}