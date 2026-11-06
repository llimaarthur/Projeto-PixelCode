// Returns active blocks for the requested period within the user's schedule scope.
query "appointments/blocks" verb=GET {
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
      error = "O intervalo de consulta dos bloqueios é inválido."
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

    db.query schedule_block {
      where = (
        $db.schedule_block.status == "active"
        && $db.schedule_block.start_at < $input.day_end
        && $db.schedule_block.end_at > $input.day_start
        && (
          $db.schedule_block.professional_id == null
          || $target_professional_id == 0
          || $db.schedule_block.professional_id == $target_professional_id
        )
      )
      sort = {schedule_block.start_at: "asc", schedule_block.id: "asc"}
      return = {type: "list"}
    } as $blocks
  }

  response = $blocks
  guid = "v8K2mN5qR1sT7wX0aC3dF6hJ9pL"
}
