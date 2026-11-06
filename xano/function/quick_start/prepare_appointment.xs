// Validates active references, builds service snapshots and rejects schedule conflicts.
function "Quick Start/prepare_appointment" {
  input {
    int contact_id
    int professional_id
    json service_ids
    timestamp start_at
    int exclude_appointment_id?
  }

  stack {
    db.get contact {
      field_name = "id"
      field_value = $input.contact_id
      output = ["id", "name", "phone", "status"]
    } as $contact

    precondition ($contact != null) {
      error_type = "inputerror"
      error = "Selecione um cliente ativo."
    }

    precondition ($contact.status == "active") {
      error_type = "inputerror"
      error = "Selecione um cliente ativo."
    }

    db.get user {
      field_name = "id"
      field_value = $input.professional_id
      output = ["id", "name", "status", "role"]
    } as $professional

    precondition ($professional != null) {
      error_type = "inputerror"
      error = "Selecione um profissional ativo."
    }

    precondition ($professional.status == "active" || $professional.status == "enabled") {
      error_type = "inputerror"
      error = "Selecione um profissional ativo."
    }

    precondition ($professional.role == "professional" || $professional.role == "admin") {
      error_type = "inputerror"
      error = "Selecione um profissional ativo."
    }

    precondition ($input.service_ids != null && ($input.service_ids|count) > 0) {
      error_type = "inputerror"
      error = "Selecione ao menos um serviço ativo."
    }

    var $service_snapshots {
      value = []
    }

    var $processed_service_ids {
      value = []
    }

    var $total_price {
      value = 0
    }

    var $total_duration {
      value = 0
    }

    foreach ($input.service_ids) {
      each as serviceId {
        array.has ($processed_service_ids) if (`$this == $serviceId`) as $duplicate_service

        precondition ($duplicate_service == false) {
          error_type = "inputerror"
          error = "Não selecione o mesmo serviço mais de uma vez."
        }

        array.push $processed_service_ids {
          value = $serviceId
        }

        db.get service {
          field_name = "id"
          field_value = $serviceId
          output = ["id", "name", "price", "duration_minutes", "status"]
        } as $service

        precondition ($service != null) {
          error_type = "inputerror"
          error = "Um ou mais serviços não estão ativos ou não existem."
        }

        precondition ($service.status == "active") {
          error_type = "inputerror"
          error = "Um ou mais serviços não estão ativos ou não existem."
        }

        array.push $service_snapshots {
          value = $service
        }

        math.add $total_price {
          value = $service.price
        }

        math.add $total_duration {
          value = $service.duration_minutes
        }
      }
    }

    var $end_at {
      value = $input.start_at|add_secs_to_timestamp:($total_duration * 60)
    }

    function.run "Quick Start/validate_working_interval" {
      input = {
        start_at: $input.start_at
        end_at: $end_at
      }
    } as $working_interval_check

    var $exclude_appointment_id {
      value = 0
    }

    conditional {
      if ($input.exclude_appointment_id != null) {
        var.update $exclude_appointment_id {
          value = $input.exclude_appointment_id
        }
      }
    }

    db.query appointment {
      where = (
        $db.appointment.professional_id == $input.professional_id
        && $db.appointment.status != "cancelled"
        && $db.appointment.start_at < $end_at
        && $db.appointment.end_at > $input.start_at
        && $db.appointment.id != $exclude_appointment_id
      )
      return = {type: "list"}
    } as $conflicts

    precondition (($conflicts|count) == 0) {
      error_type = "inputerror"
      error = "Este horário se sobrepõe a outro atendimento do profissional."
    }

    db.query schedule_block {
      where = (
        $db.schedule_block.status == "active"
        && (
          $db.schedule_block.professional_id == null
          || $db.schedule_block.professional_id == $input.professional_id
        )
        && $db.schedule_block.start_at < $end_at
        && $db.schedule_block.end_at > $input.start_at
      )
      return = {type: "list"}
    } as $block_conflicts

    precondition (($block_conflicts|count) == 0) {
      error_type = "inputerror"
      error = "Este horário está bloqueado na agenda do profissional."
    }
  }

  response = {
    contact_name_snapshot : $contact.name
    contact_phone_snapshot: $contact.phone
    professional_name_snapshot: $professional.name
    end_at          : $end_at
    total_price     : $total_price
    duration_minutes: $total_duration
    services_snapshot: $service_snapshots
  }
  guid = "95cvZLsMaqe_4arlWi28YdpS7C0"
}
