// Saves the shared weekly opening hours for the authenticated barbershop.
query "appointments/working-hours" verb=PATCH {
  api_group = "Appointments"
  auth = "user"

  input {
    json weekly_hours
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $auth.id
        required_role: "admin"
      }
    } as $role_check

    function.run "Quick Start/validate_working_hours" {
      input = {
        weekly_hours: $input.weekly_hours
      }
    } as $hours_check

    db.edit barbershop {
      field_name = "id"
      field_value = $role_check.barbershop_id
      data = {
        weekly_hours: $input.weekly_hours
      }
    } as $barbershop
  }

  response = {
    weekly_hours: $barbershop.weekly_hours
  }
  guid = "s4v3W0rkH0urs7Q9m2K5vB8x"
}
