// Creates an appointment after validating references, permissions and schedule conflicts.
query "appointments" verb=POST {
  api_group = "Appointments"
  auth = "user"

  input {
    int contact_id
    int professional_id
    json service_ids
    timestamp start_at
    text notes? filters=trim
  }

  stack {
    function.run "Quick Start/authorize_professional_scope" {
      input = {
        actor_id: $auth.id
        target_professional_id: $input.professional_id
      }
    } as $scope_check

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
      }
    } as $prepared

    db.add appointment {
      data = {
        created_at       : "now"
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
        status           : "pending"
      }
    } as $appointment
  }

  response = $appointment
  guid = "wz4AQ-BEWCnM3aBbzQ1Gbd8ckyw"
}
