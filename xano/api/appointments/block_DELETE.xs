// Releases a manual block without deleting its audit history.
query "appointments/blocks/{block_id}" verb=DELETE {
  api_group = "Appointments"
  auth = "user"

  input {
    int block_id
  }

  stack {
    db.get schedule_block {
      field_name = "id"
      field_value = $input.block_id
    } as $block

    precondition ($block != null && $block.status == "active") {
      error_type = "inputerror"
      error = "Bloqueio não encontrado ou já liberado."
    }

    var $target_professional_id {
      value = 0
    }

    conditional {
      if ($block.professional_id == null) {
        db.get user {
          field_name = "id"
          field_value = $auth.id
          output = ["id", "role", "status", "must_change_password"]
        } as $actor

        precondition ($actor.role == "admin") {
          error_type = "accessdenied"
          error = "Somente administradores podem liberar bloqueios de toda a equipe."
        }
      }
      else {
        var.update $target_professional_id {
          value = $block.professional_id
        }
      }
    }

    function.run "Quick Start/authorize_professional_scope" {
      input = {
        actor_id: $auth.id
        target_professional_id: $target_professional_id
      }
    } as $scope_check

    db.edit schedule_block {
      field_name = "id"
      field_value = $input.block_id
      data = {
        updated_at: "now"
        status    : "released"
      }
    } as $released_block
  }

  response = $released_block
  guid = "c9P2vM5kR1tX7wN0aF3hJ6sL8qB"
}
