// Assigns contacts to a professional only when an administrator requests it.
function "Quick Start/resolve_contact_owner" {
  input {
    int actor_id
    int barbershop_id
    bool include_legacy_rows?=false
    int requested_professional_id?
    int existing_professional_id?
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $input.actor_id
      output = ["id", "role"]
    } as $actor

    var $professional_id {
      value = $input.existing_professional_id
    }

    conditional {
      if ($actor.role == "professional") {
        precondition ($input.requested_professional_id == null) {
          error_type = "accessdenied"
          error = "Profissionais não podem transferir clientes."
        }

        var.update $professional_id {
          value = $actor.id
        }
      }
      else {
        conditional {
          if ($input.requested_professional_id != null) {
            conditional {
              if ($input.requested_professional_id == 0) {
                var.update $professional_id {
                  value = null
                }
              }
              else {
                conditional {
                  if ($input.requested_professional_id != $input.existing_professional_id) {
                    db.get user {
                      field_name = "id"
                      field_value = $input.requested_professional_id
                      output = ["id", "role", "status", "barbershop_id"]
                    } as $target_professional

                    precondition (
                      $target_professional != null
                      && $target_professional.role == "professional"
                      && ($target_professional.status == "active" || $target_professional.status == "enabled")
                      && (
                        $target_professional.barbershop_id == $input.barbershop_id
                        || (
                          $input.include_legacy_rows == true
                          && $target_professional.barbershop_id == null
                        )
                      )
                    ) {
                      error_type = "inputerror"
                      error = "Selecione um profissional ativo da sua barbearia."
                    }

                    var.update $professional_id {
                      value = $target_professional.id
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }

  response = {
    professional_id: $professional_id
  }
  guid = "rC0nT4ct0wn3r7Q9m2K5vB8x"
}
