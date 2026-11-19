// Returns the authenticated barbershop's shared weekly opening hours.
query "appointments/working-hours" verb=GET {
  api_group = "Appointments"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $auth.id
        required_role: "professional"
      }
    } as $role_check

    function.run "Quick Start/get_barbershop_working_hours" {
      input = {
        barbershop_id: $role_check.barbershop_id
      }
    } as $schedule
  }

  response = {
    weekly_hours: $schedule.weekly_hours
  }
  guid = "g3tW0rkH0urs7Q9m2K5vB8x"
}
