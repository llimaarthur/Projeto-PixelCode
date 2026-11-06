// Creates a manual block after validating professional scope and active appointments.
query "appointments/blocks" verb=POST {
  api_group = "Appointments"
  auth = "user"

  input {
    int professional_id
    timestamp start_at
    timestamp end_at
    text reason? filters=trim
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "role", "status", "must_change_password"]
    } as $actor

    precondition ($actor != null && ($actor.status == "active" || $actor.status == "enabled")) {
      error_type = "accessdenied"
      error = "Conta profissional ativa obrigatória."
    }

    precondition ($actor.must_change_password != true) {
      error_type = "accessdenied"
      error = "É necessário trocar a senha antes de acessar a agenda."
    }

    precondition ($input.start_at < $input.end_at) {
      error_type = "inputerror"
      error = "O fim do bloqueio deve ser posterior ao início."
    }

    function.run "Quick Start/validate_working_interval" {
      input = {
        start_at: $input.start_at
        end_at: $input.end_at
      }
    } as $working_interval_check

    var $end_minute {
      value = ($input.end_at|format_timestamp:"i":"America/Sao_Paulo")|to_int
    }

    var $end_second {
      value = ($input.end_at|format_timestamp:"s":"America/Sao_Paulo")|to_int
    }

    precondition (($end_minute == 0 || $end_minute == 30) && $end_second == 0) {
      error_type = "inputerror"
      error = "Os bloqueios devem terminar em intervalos de 30 minutos."
    }

    precondition ($input.reason == null || ($input.reason|strlen) <= 200) {
      error_type = "inputerror"
      error = "O motivo do bloqueio deve ter no máximo 200 caracteres."
    }

    var $professional_reference {
      value = null
    }

    conditional {
      if ($input.professional_id == 0) {
        precondition ($actor.role == "admin") {
          error_type = "accessdenied"
          error = "Somente administradores podem bloquear toda a equipe."
        }
      }
      else {
        var.update $professional_reference {
          value = $input.professional_id
        }

        function.run "Quick Start/authorize_professional_scope" {
          input = {
            actor_id: $auth.id
            target_professional_id: $input.professional_id
          }
        } as $scope_check
      }
    }

    db.query appointment {
      where = (
        $db.appointment.status != "cancelled"
        && $db.appointment.start_at < $input.end_at
        && $db.appointment.end_at > $input.start_at
        && (
          $input.professional_id == 0
          || $db.appointment.professional_id == $input.professional_id
        )
      )
      return = {type: "list"}
    } as $appointment_conflicts

    precondition (($appointment_conflicts|count) == 0) {
      error_type = "inputerror"
      error = "Não é possível bloquear um intervalo com atendimento ativo."
    }

    db.add schedule_block {
      data = {
        created_at      : "now"
        updated_at      : "now"
        professional_id : $professional_reference
        start_at        : $input.start_at
        end_at          : $input.end_at
        reason          : $input.reason
        status          : "active"
      }
    } as $block
  }

  response = $block
  guid = "b4N7qR2mK9xT1vW5cF8hJ3sL6pA"
}
