// Returns appointments for a day while enforcing professional scope.
query "appointments" verb=GET {
  api_group = "Appointments"
  auth = "user"

  input {
    timestamp day_start
    timestamp day_end
    int professional_id?
  }

  stack {
    precondition ($input.day_start < $input.day_end) {
      error_type = "inputerror"
      error = "O intervalo de consulta da agenda é inválido."
    }

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

    var $target_professional_id {
      value = $auth.id
    }

    conditional {
      if ($actor.role == "admin") {
        var.update $target_professional_id {
          value = 0
        }
      }
    }

    conditional {
      if ($actor.role == "admin" && $input.professional_id != null && $input.professional_id > 0) {
        var.update $target_professional_id {
          value = $input.professional_id
        }
      }
    }

    function.run "Quick Start/authorize_professional_scope" {
      input = {
        actor_id: $auth.id
        target_professional_id: $target_professional_id
      }
    } as $scope_check

    db.query appointment {
      where = (
        $db.appointment.start_at < $input.day_end
        && $db.appointment.end_at > $input.day_start
        && ($target_professional_id == 0 || $db.appointment.professional_id == $target_professional_id)
      )
      sort = {appointment.start_at: "asc", appointment.id: "asc"}
      return = {type: "list"}
    } as $appointments
  }

  response = $appointments
  guid = "UpXL4lTxgBFKMOvBgFxZDRmkY4g"
}
