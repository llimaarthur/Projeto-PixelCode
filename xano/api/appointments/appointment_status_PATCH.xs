// Changes the appointment status without deleting its history.
query "appointments/{appointment_id}/status" verb=PATCH {
  api_group = "Appointments"
  auth = "user"

  input {
    int appointment_id
    enum status {
      values = ["pending", "confirmed", "completed", "cancelled"]
    }
  }

  stack {
    db.get appointment {
      field_name = "id"
      field_value = $input.appointment_id
    } as $appointment

    precondition ($appointment != null) {
      error_type = "inputerror"
      error = "Agendamento não encontrado."
    }

    function.run "Quick Start/authorize_professional_scope" {
      input = {
        actor_id: $auth.id
        target_professional_id: $appointment.professional_id
      }
    } as $scope_check

    precondition (
      $input.status == $appointment.status
      || (
        $appointment.status == "pending"
        && ($input.status == "confirmed" || $input.status == "cancelled")
      )
      || (
        $appointment.status == "confirmed"
        && ($input.status == "completed" || $input.status == "cancelled")
      )
    ) {
      error_type = "inputerror"
      error = "Transição de status inválida. Agendamentos concluídos ou cancelados não podem ser reabertos."
    }

    db.edit appointment {
      field_name = "id"
      field_value = $input.appointment_id
      data = {
        updated_at: "now"
        status    : $input.status
      }
    } as $updated_appointment
  }

  response = $updated_appointment
  guid = "xjllPWSkl-81V8upWA8CndibvXQ"
}
