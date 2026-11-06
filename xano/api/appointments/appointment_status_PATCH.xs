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

    conditional {
      if ($appointment.status == "cancelled" && $input.status != "cancelled") {
        function.run "Quick Start/validate_working_interval" {
          input = {
            start_at: $appointment.start_at
            end_at: $appointment.end_at
          }
        } as $working_interval_check

        db.query appointment {
          where = (
            $db.appointment.professional_id == $appointment.professional_id
            && $db.appointment.id != $appointment.id
            && $db.appointment.status != "cancelled"
            && $db.appointment.start_at < $appointment.end_at
            && $db.appointment.end_at > $appointment.start_at
          )
          return = {type: "list"}
        } as $conflicts

        precondition (($conflicts|count) == 0) {
          error_type = "inputerror"
          error = "Não é possível reativar este agendamento: o horário está ocupado."
        }

        db.query schedule_block {
          where = (
            $db.schedule_block.status == "active"
            && (
              $db.schedule_block.professional_id == null
              || $db.schedule_block.professional_id == $appointment.professional_id
            )
            && $db.schedule_block.start_at < $appointment.end_at
            && $db.schedule_block.end_at > $appointment.start_at
          )
          return = {type: "list"}
        } as $block_conflicts

        precondition (($block_conflicts|count) == 0) {
          error_type = "inputerror"
          error = "Não é possível reativar este agendamento: o horário está bloqueado."
        }
      }
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
