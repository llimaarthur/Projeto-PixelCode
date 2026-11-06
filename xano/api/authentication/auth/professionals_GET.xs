// Returns the active team members to an administrator.
query "auth/professionals" verb=GET {
  api_group = "Authentication"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check

    db.query user {
      where = (
        ($db.user.role == "professional" || $db.user.role == "admin")
        && ($db.user.status == "active" || $db.user.status == "enabled")
      )
      sort = {user.name: "asc"}
      output = ["id", "name", "email", "phone", "role", "profile_photo_url"]
      return = {type: "list"}
    } as $professionals
  }

  response = $professionals
  guid = "pR0f3ss10n4lsGEt20261103"
}
