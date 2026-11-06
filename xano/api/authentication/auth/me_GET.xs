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
      output = ["id", "created_at", "name", "email", "phone", "cpf",       "profile_photo_url", "profile_photo_public_id", "role", "status", "must_change_password"]
    } as $user

    precondition ($user.status == "active" || $user.status == "enabled") {
      error_type = "accessdenied"
      error = "User account is inactive."
    }

    // Create an event log for get user record
    function.run "Quick Start/log_event" {
      input = {
        user_id : $user.id
        action  : "get_auth_user"
        metadata: {role: $user.role}
      }
    } as $event_log
  }

  response = {
    id                   : $user.id
    created_at           : $user.created_at
    name                 : $user.name
    email                : $user.email
    phone                : $user.phone
    cpf                  : $user.cpf
    profile_photo_url    : $user.profile_photo_url
    profile_photo_public_id: $user.profile_photo_public_id
    role                 : $user.role
    status               : $user.status
    must_change_password : $user.must_change_password
  }
  tags = ["xano:quick-start"]
  guid = "cRZuaT4Vx7JOu8batje6QPed5aQ"
}