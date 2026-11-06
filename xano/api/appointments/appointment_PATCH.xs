// Updates an appointment only when the authenticated user has access to that professional's schedule.
query "appointments/{appointment_id}" verb=PATCH {
  api_group = "Appointments"
  auth = "user"

  input {
    int appointment_id
    int contact_id
    int professional_id
    json service_ids
    timestamp start_at
    text notes? filters=trim
  }

  stack {
    db.get appointment {
      field_name = "id"
      field_value = $input.appointment_id
    } as $existing_appointment

    precondition ($existing_appointment != null) {
      error_type = "inputerror"
      error = "Agendamento não encontrado."
    }

    precondition ($existing_appointment.status != "completed" && $existing_appointment.status != "cancelled") {
      error_type = "inputerror"
      error = "Atendimentos concluídos ou cancelados não podem ser editados."
    }

    function.run "Quick Start/authorize_professional_scope" {
      input = {
        actor_id: $auth.id
        target_professional_id: $existing_appointment.professional_id
      }
    } as $existing_scope_check

    function.run "Quick Start/authorize_professional_scope" {
      input = {
        actor_id: $auth.id
        target_professional_id: $input.professional_id
      }
    } as $target_scope_check

    precondition ($input.notes == null || ($input.notes|strlen) <= 1000) {
      error_type = "inputerror"
      error = "As observações devem ter no máximo 1000 caracteres."
    }

    function.run "Quick Start/prepare_appointment" {
      input = {
        contact_id: $input.contact_id
        professional_id: $input.professional_id
        service_ids: $input.service_ids
        start_at: $input.start_at
        exclude_appointment_id: $input.appointment_id
      }
    } as $prepared

    db.edit appointment {
      field_name = "id"
      field_value = $input.appointment_id
      data = {
        updated_at       : "now"
        contact_id       : $input.contact_id
        contact_name_snapshot: $prepared.contact_name_snapshot
        contact_phone_snapshot: $prepared.contact_phone_snapshot
        professional_id  : $input.professional_id
        professional_name_snapshot: $prepared.professional_name_snapshot
        start_at         : $input.start_at
        end_at           : $prepared.end_at
        duration_minutes : $prepared.duration_minutes
        total_price      : $prepared.total_price
        services_snapshot: $prepared.services_snapshot
        notes            : $input.notes
      }
    } as $appointment
  }

  response = $appointment
  guid = "C_JU_SwbAYwN2sUtzxk7x_AAWU0"
}
