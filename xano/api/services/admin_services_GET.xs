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
      where = (
        $db.service.barbershop_id == $role_check.barbershop_id
        || ($role_check.include_legacy_rows == true && $db.service.barbershop_id == null)
      )
      return = {type: "list"}
    } as $services
  }

  response = $services
  guid = "dXgzGxC3uyzw6hL3ufhwO0yu2Xo"
}
