// Get the user record belonging to the authentication token
query "auth/me" verb=GET {
  api_group = "Authentication"
  auth = "user"

  input {
  }

  stack {
    // Get the user record based on the auth ID
    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "created_at", "name", "email", "role"]
    } as $user
  
    // Create an event log for get user record
    function.run "Quick Start/log_event" {
      input = {
        user_id : $user.id
        action  : "get_auth_user"
        metadata: $user
      }
    } as $event_log
  }

  response = $user
  tags = ["xano:quick-start"]
  guid = "cRZuaT4Vx7JOu8batje6QPed5aQ"
}