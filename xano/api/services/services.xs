// Authenticated professionals can only query active services.
query "services" verb=GET {
  api_group = "Services"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "professional"}
    } as $role_check

    db.query service {
      where = (
        (
          $db.service.barbershop_id == $role_check.barbershop_id
          || ($role_check.include_legacy_rows == true && $db.service.barbershop_id == null)
        )
        && $db.service.status == "active"
      )
      return = {type: "list"}
    } as $services
  }

  response = $services
  guid = "2XKel2K1YVv7Z38HrfU_AlwzyQU"
}
