// Administrators can query both active and inactive services.
query "services/admin" verb=GET {
  api_group = "Services"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check

    db.query service {
      return = {type: "list"}
    } as $services
  }

  response = $services
}
