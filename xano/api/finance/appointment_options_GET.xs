// Returns pending appointments that can be linked to a service payment.
query "finance/appointment-options" verb=GET {
  api_group = "Finance"
  auth = "user"

  input {
    int contact_id?
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $auth.id
        required_role: "professional"
      }
    } as $access_check

    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "role"]
    } as $actor

    conditional {
      if ($input.contact_id != null) {
        db.get contact {
          field_name = "id"
          field_value = $input.contact_id
          output = ["id", "barbershop_id", "professional_id"]
        } as $contact

        precondition (
          $contact != null
          && (
            $contact.barbershop_id == $access_check.barbershop_id
            || ($access_check.include_legacy_rows == true && $contact.barbershop_id == null)
          )
          && ($actor.role == "admin" || $contact.professional_id == $auth.id)
        ) {
          error_type = "inputerror"
          error = "Cliente não encontrado."
        }
      }
    }

    db.query appointment {
      where = (
        ($db.appointment.status == "pending" || $db.appointment.status == "confirmed")
        && (
          $db.appointment.barbershop_id == $access_check.barbershop_id
          || ($access_check.include_legacy_rows == true && $db.appointment.barbershop_id == null)
        )
        && ($input.contact_id == null || $db.appointment.contact_id == $input.contact_id)
        && ($actor.role == "admin" || $db.appointment.professional_id == $auth.id)
      )
      sort = {appointment.start_at: "asc", appointment.id: "asc"}
      return = {type: "list"}
    } as $appointments
  }

  response = $appointments
  guid = "F4sJ8nQ2wL7pC1vM9aR5dK"
}
